import logging
import os
import pprint
import sys
import tempfile as tmp
import joblib

if sys.platform == 'darwin':
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
os.environ['JOBLIB_TEMP_FOLDER'] = tmp.gettempdir()
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

from tpot import TPOTClassifier, TPOTRegressor, __version__

from frameworks.shared.callee import call_run, output_subdir, result
from frameworks.shared.utils import Timer


log = logging.getLogger(__name__)


def run(dataset, config):
    log.info(f"\n**** TPOT [v{__version__}]****\n")

    is_classification = config.type == 'classification'
    # Mapping of benchmark metrics to TPOT metrics
    metrics_mapping = dict(
        acc='accuracy',
        auc='roc_auc',
        f1='f1',
        logloss='neg_log_loss',
        mae='neg_mean_absolute_error',
        mse='neg_mean_squared_error',
        msle='neg_mean_squared_log_error',
        r2='r2',
        rmse='neg_mean_squared_error',  # TPOT can score on mse, as app computes rmse independently on predictions
    )
    scoring_metric = metrics_mapping[config.metric] if config.metric in metrics_mapping else None
    if scoring_metric is None:
        raise ValueError("Performance metric {} not supported.".format(config.metric))

    X_train = dataset.train.X
    y_train = dataset.train.y

    training_params = {k: v for k, v in config.framework_params.items() if not k.startswith('_')}
    n_jobs = config.framework_params.get('_n_jobs', config.cores)  # useful to disable multicore, regardless of the dataset config

    log.info('Running TPOT with a maximum time of %ss on %s cores, optimizing %s.',
             config.max_runtime_seconds, n_jobs, scoring_metric)
    runtime_min = (config.max_runtime_seconds/60)

    if config.task_type == 'train':
        estimator = TPOTClassifier if is_classification else TPOTRegressor
        tpot = estimator(n_jobs=n_jobs,
                         max_time_mins=runtime_min,
                         scoring=scoring_metric,
                         random_state=config.seed,
                         **training_params)

        with Timer() as training:
            tpot.fit(X_train, y_train)
        training_duration = training.duration
        models_count = len(tpot.evaluated_individuals_)

        # save model
        model_path = tmp.mkdtemp()
        try:
            log.info('Saving model to %s', model_path)
            joblib.dump(tpot.fitted_pipeline_, os.path.join(model_path, 'model.joblib'))
        except:
            log.exception('Error saving model to %s', model_path)
            model_path = None

    elif config.task_type == 'predict':
        log.info('Loading model from %s', config.model_path)
        tpot = joblib.load(os.path.join(config.model_path, 'model.joblib'))
        training_duration = 0.0
        model_path = None
        models_count = 1

    log.info('Predicting on the test set.')
    X_test = dataset.test.X
    y_test = dataset.test.y
    with Timer() as predict:
        predictions = tpot.predict(X_test)
    try:
        probabilities = tpot.predict_proba(X_test) if is_classification else None
    except RuntimeError:
        # TPOT throws a RuntimeError if the optimized pipeline does not support `predict_proba`.
        probabilities = "predictions"  # encoding is handled by caller in `__init__.py`

    if config.task_type == 'train':
        # during predict, tpot is just a pipeline object
        save_artifacts(tpot, config)

    return result(output_file=config.output_predictions_file,
                  predictions=predictions,
                  truth=y_test,
                  probabilities=probabilities,
                  target_is_encoded=is_classification,
                  models_count=models_count,
                  training_duration=training_duration,
                  predict_duration=predict.duration,
                  model_path=model_path)


# TODO: export the python code for the best pipeline via tpot.export
def save_artifacts(estimator, config):
    try:
        log.debug("All individuals :\n%s", list(estimator.evaluated_individuals_.items()))
        models = estimator.pareto_front_fitted_pipelines_
        hall_of_fame = list(zip(reversed(estimator._pareto_front.keys), estimator._pareto_front.items))
        artifacts = config.framework_params.get('_save_artifacts', False)
        if 'models' in artifacts:
            models_file = os.path.join(output_subdir('models', config), 'models.txt')
            with open(models_file, 'w') as f:
                for m in hall_of_fame:
                    pprint.pprint(dict(
                        fitness=str(m[0]),
                        model=str(m[1]),
                        pipeline=models[str(m[1])],
                    ), stream=f)
    except Exception:
        log.debug("Error when saving artifacts.", exc_info=True)


if __name__ == '__main__':
    call_run(run)
