class ExperimentServerExcetion(Exception):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(args, kwargs)


class ExperimentServerConfigurationExcetion(Exception):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(args, kwargs)

# From: https://cs.uwaterloo.ca/~dmasson/tools/latin_square/
# Based on "Bradley, J. V. Complete counterbalancing of immediate sequential effects in a Latin square design. J. Amer. Statist. Ass.,.1958, 53, 525-528. "
def balanced_latin_square(number_of_conditions):
    latin_square = []

    for participant_idx in range(number_of_conditions):
        j = 0
        h = 0

        trials = []
        for trial_idx in range(number_of_conditions):
            val = 0
            if trial_idx < 2 or trial_idx % 2 != 0:
                val = j
                j += 1
            else:
                val = number_of_conditions - h -1
                h += 1

            trials.append((val + participant_idx) % number_of_conditions)

        latin_square.append(trials)
        if number_of_conditions % 2 != 0:
            latin_square.append(trials[::-1])

    return latin_square
