# Documentation of experiment server API

## Public API
### ::: experiment_server.Experiment
      
### ::: experiment_server.Client

### ::: experiment_server.server_process

## Full API
### ::: experiment_server._api
     options:
       members:
       - ParticipantState
       - _generate_config_json
### ::: experiment_server._process_config
     options:
       members:
       - process_config_file
       - resolve_extends
       - _replace_variables
       - resolve_function_calls
       - ChoicesFunction
       - verify_config
### ::: experiment_server._participant_ordering
     options:
       members:
       - construct_participant_condition

### ::: experiment_server.utils
     options:
       members:
       - FileModifiedWatcher
       - balanced_latin_square
       - merge_dicts
