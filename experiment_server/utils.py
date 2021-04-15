class ExperimentServerExcetion(Exception):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(args, kwargs)


class ExperimentServerConfigurationExcetion(Exception):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(args, kwargs)
