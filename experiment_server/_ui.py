"""
Textual UI for experiment_server

Usage:
    python -m experiment_server._ui --config path/to/config.toml
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Dict, Optional, Iterable
from loguru import logger
import asyncio
from tabulate import tabulate

from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll,HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.widgets import (
    DirectoryTree,
    Header,
    Footer,
    Button,
    Input,
    Label,
    Static,
    DataTable,
    TabbedContent,
    TabPane,
    Pretty,
    RichLog,
    Collapsible,
    Switch,
    TextArea
)
from experiment_server._api import Experiment, _generate_config_json
from experiment_server._process_config import _process_config, _get_table_for_participants
from experiment_server.utils import new_config_file
from experiment_server._server import start_server_in_current_ioloop
import toml  # type: ignore


def pretty_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


class TomlFilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if path.is_dir() or path.suffix == ".toml"]


class LoadConfig(ModalScreen[Path]):  
    """Screen with a dialog to load confi."""

    def __init__(self, current_path):
        super().__init__()
        self.current_path = current_path
        self.selected_path = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Select config file to load")
            yield TomlFilteredDirectoryTree("")
            with Horizontal():
                yield Button("Load", id="load_config_load")
                yield Button("Cancel", id="load_config_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "load_config_load":
            self.dismiss(self.selected_path)
        else:
            self.dismiss(None)

    def on_directory_tree_file_selected(self, file_selected: DirectoryTree.FileSelected):
        self.selected_path = file_selected.path


class ParticipantTab(Vertical):
    """Participant management tab."""
    def __init__(self, experiment:Experiment):
        super().__init__()
        self.experiment = experiment

        # Widgets
        self.update_ppid_input = Input(placeholder=str(self.experiment.default_participant_index), id="update_ppid_input")
        self.status_box = Static(id="status_box")
        self.block_input = Input(placeholder="block id", id="block_input")
        self.block_all_input = Input(placeholder="block id (for all)", id="block_all_input")
        self.participants_table = DataTable(id="participants_table")
        self.config_pretty = Pretty("", id="config_pretty")

        self.monitor_default_switch = Switch(value=True)
        self.monitor_input = Input(placeholder="participant id (empty = default)", id="monitor_input", disabled=True)
        self.participant_id_to_add_input = Input(placeholder="participant id", id="participant_id_to_add_input")
        self.edit_container = Grid(id="edit_container")

        self.participants_table.add_column("participant_id")
        self.participants_table.add_column("block_id")
        self.participants_table.add_column("block_name")
        self.participants_table.add_column("active")

        # editable inputs map when editing config
        self._edit_inputs: Dict[str, Input] = {}

    def compose(self):
        with Grid(id="participant_summary_grid"):
            yield Static("Default participant id:")
            yield self.update_ppid_input
            yield Button("Update default ppid", id="btn_update_ppid")
        with VerticalScroll():
            with Collapsible(title="Manage block config:", id="collapse_status", collapsed=False):
                yield Label("Current status:")
                yield self.status_box
                with Grid(id="status_grid"):
                    yield Button("Move to next", id="btn_move_next")
                    yield Static()  # empty grid
                    yield self.block_input
                    yield Button("Move to block", id="btn_move_to_block")

            with Collapsible(title="Current block config:", id="collapse_block_config"):
                yield self.config_pretty
                with Grid(id="config_grid"):
                    yield Button("Edit block config", id="btn_edit_config")
                    yield Button("Reset participant", id="btn_reset_participant")
                yield self.edit_container

            with Collapsible(title="All participants states:", id="collapse_states"):
                yield self.participants_table
                with Grid(id="states_grid"):
                    yield Static()  # empty grid
                    yield self.block_all_input
                    yield Button("Move all to block", id="btn_move_all_to_block")

                    yield Static("Monitor default ppid: ", id="static_monitor_ppid")
                    yield self.monitor_default_switch
                    yield Static()  # empty grid

                    yield Static()  # empty grid
                    yield self.monitor_input
                    yield Button("Set participant to monitor", id="btn_set_monitor", disabled=True)

                    yield Static("Add new participant id: ", id="static_add_new_ppid")
                    yield self.participant_id_to_add_input
                    yield Button("Add", id="btn_add_participant_with_id")

                    yield Static()  # empty grid
                    yield Button("New participant", id="btn_new_participant")
                    # yield Button("List participants", id="btn_list_participants")

        self.refresh_ui()

    # Utilities
    def _monitored_pid(self) -> Optional[int]:
        v = self.monitor_input.value.strip()
        if v == "":
            return None
        try:
            return int(v)
        except ValueError:
            return None

    def refresh_ui(self) -> None:
        pid = self._monitored_pid()
        # status
        try:
            state = self.experiment.get_participant_state(pid)
            status = state.status_string()
        except Exception as e:
            status = f"Error: {e}"

        self.update_ppid_input.placeholder = str(self.experiment.default_participant_index)
        self.status_box.update(status.replace("\n", " | "))

        # participants
        try:
            # rebuild table to avoid stale columns/rows
            self.participants_table.clear()
            for idx, st in sorted(self.experiment.global_state.items()):
                self.participants_table.add_row(str(idx), str(st.block_id), str(st.block_name), str(st.active))
        except Exception:
            # If experiment not loaded, leave table empty
            pass

        # config display
        try:
            cfg = self.experiment.get_config(pid)
            if cfg is None:
                self.config_pretty.update("Participant not active. Call Move to next first.")
            else:
                # Pretty handles objects nicely; pass the dict so it renders prettily
                self.config_pretty.update(cfg)
        except Exception as e:
            self.config_pretty.update(f"Error: {e}")

    # Actions (synchronous Experiment API usage)
    def move_next(self) -> None:
        pid = self._monitored_pid()
        try:
            name = self.experiment.move_to_next(pid)
            logger.info(f"Moved to next block: {name}")
        except Exception as e:
            logger.error(f"Error moving to next: {e}")
        self.refresh_ui()

    def move_to_block(self) -> None:
        pid = self._monitored_pid()
        v = self.block_input.value.strip()
        try:
            bid = int(v)
        except Exception:
            logger.error("Invalid block id")
            return
        try:
            name = self.experiment.move_to_block(bid, pid)
            logger.info(f"Moved participant {pid or 'default'} to block {bid} ({name})")
        except Exception as e:
            logger.error(f"Error moving to block: {e}")
        self.refresh_ui()

    def reset_participant(self) -> None:
        pid = self._monitored_pid()
        try:
            self.experiment.reset_participant(pid)
            logger.info(f"Reset participant {pid or 'default'}")
        except Exception as e:
            logger.error(f"Error resetting participant: {e}")
        self.refresh_ui()

    def list_participants(self) -> None:
        try:
            self.participants_table.clear()
            for idx, st in sorted(self.experiment.global_state.items()):
                self.participants_table.add_row(str(idx), str(st.block_id), str(st.block_name), str(st.active))
            logger.info("Listed participants")
        except Exception as e:
            logger.error(f"Error listing participants: {e}")

    def move_all_to_block(self) -> None:
        v = self.block_all_input.value.strip()
        try:
            bid = int(v)
        except Exception:
            logger.error("Invalid block id")
            return
        try:
            name = self.experiment.move_all_to_block(bid)
            logger.info(f"Moved all participants to block {bid} ({name})")
        except Exception as e:
            logger.error(f"Error moving all: {e}")
        self.refresh_ui()

    def set_monitor(self) -> None:
        pid = self._monitored_pid()
        if pid is None:
            logger.info("Monitoring default participant")
        else:
            if pid not in getattr(self.experiment, "global_state", {}):
                logger.info(f"Participant {pid} not known. Use New participant to add.")
            else:
                logger.info(f"Now monitoring participant {pid}")
        self.refresh_ui()

    def new_participant(self) -> None:
        try:
            new_id = self.experiment.get_next_participant()
            logger.info(f"Created new participant {new_id}")
        except Exception as e:
            logger.error(f"Error creating participant: {e}")
        self.refresh_ui()

    def new_participant_with_id(self) -> None:
        v = self.participant_id_to_add_input.value.strip()
        try:
            id = int(v)
        except Exception:
            logger.error("Invalid participant id")
            return
        try:
            new_id = self.experiment.add_participant_index(id)
            logger.info(f"Created new participant {new_id}")
        except Exception as e:
            logger.error(f"Error creating participant: {e}")
        self.refresh_ui()

    def update_ppid(self):
        v = self.update_ppid_input.value.strip()
        self.update_ppid_input.clear()
        try:
            ppid = int(v)
        except Exception:
            logger.error("Invalid ppid")
            return
        try:
            self.experiment.default_participant_index = ppid
        except Exception as e:
            logger.error(f"Error moving to block: {e}")
        self.refresh_ui()

    # Config editing
    def start_edit_config(self) -> None:
        pid = self._monitored_pid()
        try:
            cfg = self.experiment.get_config(pid)
        except Exception as e:
            logger.error(f"Cannot edit config: {e}")
            return
        if cfg is None:
            logger.info("Participant not active. Call Move to next first.")
            return

        # clear prior edit inputs
        self._edit_inputs.clear()

        for child in list(self.edit_container.children):
            child.remove()

        self.edit_container.mount(Static("Edit keys (enter JSON literals):", classes="edit_title"))
        for k, v in cfg.items():
            if k in ("participant_index", "block_id", "name"):
                self.edit_container.mount(Static(f"{k} (immutable):", classes="edit_label"))
                self.edit_container.mount(Static(str(v), classes="edit_value_immutable"))
                continue
            inp = Input(placeholder=json.dumps(v, ensure_ascii=False), id=f"edit_{k}", classes="edit_value")
            self._edit_inputs[k] = inp
            self.edit_container.mount(Static(f"{k}:", classes="edit_label"))
            self.edit_container.mount(inp)

        self.edit_container.mount(Button("Submit edits", id="btn_submit_edits"))
        self.edit_container.mount(Button("Cancel edits", id="btn_cancel_edits"))
        self.edit_container.add_class("round_border")
        logger.info("Mounted edit inputs. Fill values and press Submit edits.")

    def submit_edits(self) -> None:
        self.edit_container.remove_class("round_border")
        if not self._edit_inputs:
            logger.info("No edits in progress.")
            return
        pid = self._monitored_pid()
        try:
            cfg = self.experiment.get_config(pid)
        except Exception as e:
            logger.error(f"Cannot submit: {e}")
            return
        if cfg is None:
            logger.info("Participant not active.")
            return

        errors = False
        for k, inp in self._edit_inputs.items():
            raw = inp.value.strip()
            if raw == "":
                continue
            try:
                val = json.loads(raw)
                cfg[k] = val
            except Exception as e:
                logger.error(f"Failed parsing {k}: {e}")
                errors = True

        if not errors:
            logger.info("Config updated in-memory.")
            for child in list(self.edit_container.children):
                child.remove()
            self._edit_inputs.clear()
        else:
            logger.info("One or more fields failed to parse; fix and submit again.")
        self.refresh_ui()

    def cancel_edits(self) -> None:
        self.edit_container.remove_class("round_border")
        self._edit_inputs.clear()
        for child in list(self.edit_container.children):
            child.remove()
        logger.info("Cancelled edits.")
        self.refresh_ui()

    # Event handler
    def on_switch_changed(self, event: Switch.Changed) -> None:
        # event.value is the new boolean state of the switch
        input_widget = self.monitor_input
        input_widget.disabled = event.value
        button = self.query_one("#btn_set_monitor", Button)
        button.disabled = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn_move_next":
            self.move_next()
        elif bid == "btn_move_to_block":
            self.move_to_block()
        elif bid == "btn_reset_participant":
            self.reset_participant()
        elif bid == "btn_list_participants":
            self.list_participants()
        elif bid == "btn_move_all_to_block":
            self.move_all_to_block()
        elif bid == "btn_set_monitor":
            self.set_monitor()
        elif bid == "btn_new_participant":
            self.new_participant()
        elif bid == "btn_add_participant_with_id":
            self.new_participant_with_id()
        elif bid == "btn_refresh":
            self.refresh_ui()
        elif bid == "btn_edit_config":
            self.start_edit_config()
        elif bid == "btn_submit_edits":
            self.submit_edits()
        elif bid == "btn_cancel_edits":
            self.cancel_edits()
        elif bid == "btn_update_ppid":
            self.update_ppid()


class ConfigTab(Vertical):
    """Manage config tab."""

    def __init__(self, experiment:Experiment):
        super().__init__()
        self.experiment = experiment
        self.experiment.on_file_change_callback.append(self.config_changed_callback)
        self.experiment.on_config_change_callback.append(self.config_changed_callback)

        self.gen_box_message = Static("")
        self._gen_box_temp_msg = None
        self.gen_cfg_path_input = Input(placeholder="output toml path", id="gen_cfg_path")

        self.new_order_input = Input(placeholder='order as JSON list, e.g. ["condA","condB"]', id="order_input")
        self.new_blocks_input = Input(placeholder='blocks as JSON list of block names', id="blocks_input")
        self.new_parameters_input = Input(placeholder='parameters as JSON list of block names', id="param_input")
        self.new_box_message = Static("")
        self._new_box_temp_msg = None
        self.new_cfg_path_input = Input(placeholder="output toml path", id="new_cfg_path")

        self.gen_json_box_message = Static("")
        self._gen_json_box_temp_msg = None
        self.gen_json_path_input = Input(placeholder="output toml path", id="gen_json_path")
        self.generate_indices_input = Input(placeholder="participant indices CSV or range (e.g. 1,2,3 or 1-5)", id="gen_indices")

        self.config_edit_message = Static("")
        self.config_order_log = RichLog(id="order_table")
        self._config_file_box_temp_msg = None
        self.config_edit_text = TextArea.code_editor(language="toml", read_only=True)

    def compose(self):
        with VerticalScroll():
            with Collapsible(title="Edit current config file:", id="collapse_edit_config"):
                with VerticalScroll():
                    with Collapsible(title="Example ordering for 5 participants"):
                        yield self.config_order_log
                    with HorizontalGroup():
                        yield Static("On save config will try to autoload")
                        yield self.config_edit_message
                    with Grid(id="edit_config_button_grid"):
                        yield Button("Edit config", id="btn_edit_config")
                        yield Button("Save config", id="btn_save_config", disabled=True)
                    yield self.config_edit_text

            with Collapsible(title="Generate new config file (simple):", id="collapse_generate_config_simple"):
                with VerticalGroup():
                    yield Static("Generate config file from sample (with examples and documentation). This will overwrite the file at destination.")
                    with HorizontalGroup():
                        yield self.gen_box_message
                    with Grid(id="generate_simple_grid"):
                        yield self.gen_cfg_path_input
                        yield Button("Generate config", id="btn_generate_simple")

            with Collapsible(title="Generate new config file (advanced):", id="collapse_generate_config_advanced"):
                with VerticalGroup():
                    yield Static("Generate config file with following fields. This will overwrite the file at destination.")
                    with HorizontalGroup():
                        yield self.new_box_message
                    with Grid(id="generate_complex_grid"):
                        yield Label("Order (as JSON list):")
                        yield self.new_order_input
                        yield Label("Blocks (as JSON list of block names):")
                        yield self.new_blocks_input
                        yield Label("Parameters (as JSON list of parameter names):")
                        yield self.new_parameters_input
                        yield self.new_cfg_path_input
                        yield Button("Generate config", id="btn_generate_advanced")

            with Collapsible(title="Generate participant json:", id="collapse_generate_pp_json"):
                with VerticalGroup():
                    yield Static("Generate JSON for a set of participants by resolving loaded config.")
                    with HorizontalGroup():
                        yield self.gen_json_box_message
                    with Grid(id="generate_json_grid"):
                        yield Label("Participant indices (CSV or range) for generation:")
                        yield self.generate_indices_input
                        yield self.gen_json_path_input
                        yield Button("Generate JSON for ppid range", id="btn_generate_json")
        self.refresh_ui()

    def config_changed_callback(self, success):
        if success:
            self._config_file_box_temp_msg = "Success"
        else:
            self._config_file_box_temp_msg = "Errors in config, check logs"
        self.refresh_ui()

    def create_config_advanced(self) -> None:
        outp = self.new_cfg_path_input.value.strip()
        if outp == "":
            self._new_box_temp_msg = "provide output toml path."
            logger.info(self._new_box_temp_msg)
            self.refresh_ui()
            return

        if not outp.endswith(".toml"):
            outp += ".toml"

        try:
            order_val = json.loads(self.new_order_input.value) if self.new_order_input.value.strip() else []
            order_val_flat = [x for item in order_val for x in (item if isinstance(item, list) else [item])]
            if not all([isinstance(i, str) for i in order_val_flat]):
                raise Exception("Order needs to be list of strings or list of list of strings.")
        except Exception as e:
            self._new_box_temp_msg = f"Failed to parse order JSON field: {e}"
            logger.error(self._new_box_temp_msg)
            self.refresh_ui()
            return

        try:
            blocks_val = json.loads(self.new_blocks_input.value) if self.new_blocks_input.value.strip() else []
            if not all([isinstance(i, str) for i in blocks_val]):
                raise Exception("Block names needs to be list of strings.")
            if not all([i in blocks_val for i in order_val_flat]):
                raise Exception("Order contains unknown block names.")
        except Exception as e:
            self._new_box_temp_msg = f"Failed to parse block JSON field: {e}"
            logger.error(self._new_box_temp_msg)
            self.refresh_ui()
            return

        try:
            parameters = json.loads(self.new_parameters_input.value) if self.new_parameters_input.value.strip() else ["parm1"]
            if not isinstance(parameters, list) or not all([isinstance(i, str) for i in parameters]):
                raise Exception("Parameters need to be list of strings.")
        except Exception as e:
            self._new_box_temp_msg = f"Failed to parse parameters JSON field: {e}"
            logger.error(self._new_box_temp_msg)
            self.refresh_ui()
            return
        minimal:dict[Any, Any] = {"blocks": []}
        params = {p: "TODO" for p in parameters}
        for name in blocks_val:
            minimal["blocks"].append({"name": name, "config": params})
        minimal["configuration"] = {"order": order_val}

        try:
            _process_config(minimal, 1, True)
        except Exception as e:
            self._new_box_temp_msg = f"Malformed configuration: {e}"
            logger.exception(self._new_box_temp_msg)
            self.refresh_ui()
            return

        p = Path(outp)
        try:
            with p.open("w", encoding="utf-8") as f:
                toml.dump(minimal, f)
            self._new_box_temp_msg = f"Wrote config to {p}"
            logger.info(self._new_box_temp_msg)
        except Exception as e:
            self._new_box_temp_msg = f"Failed to write config: {e}"
            logger.error(self._new_box_temp_msg)
        self.refresh_ui()

    def create_config_simple(self) -> None:
        outp = self.gen_cfg_path_input.value.strip()
        if outp == "":
            self._gen_box_temp_msg = "provide output toml path."
            logger.info(self._gen_box_temp_msg)
            self.refresh_ui()
            return

        if not outp.endswith(".toml"):
            outp += ".toml"

        try:
            new_config_file(outp)
            self._gen_box_temp_msg = f"Wrote to {outp}"
            logger.info(self._gen_box_temp_msg)
        except Exception as e:
            self._gen_box_temp_msg = f"Failed to write config: {e}"
            logger.error(self._gen_box_temp_msg)
        self.refresh_ui()

    # def verify_config(self) -> None:
    #     path = self.cfg_path_input.value.strip()
    #     if not path:
    #         logger.info("Provide path to config to verify.")
    #         return
    #     p = Path(path)
    #     if not p.exists():
    #         logger.info("File not found.")
    #         return
    #     try:
    #         exp = Experiment(str(p), 1)
    #         cnt = exp.get_blocks_count(None)
    #         logger.info(f"Config loaded OK. Blocks count: {cnt}")
    #         configs = exp.get_all_configs(1)
    #         if configs:
    #             logger.info("Participant 1 first block config:")
    #             logger.info(pretty_json(configs[0]))
    #     except Exception as e:
    #         logger.error(f"Verification failed: {e}")

    def generate_json(self) -> None:
        path = self.gen_json_path_input.value.strip()
        if not path:
            self._gen_json_box_temp_msg = "Provide path to config to generate from."
            logger.info(self._gen_json_box_temp_msg)
            self.refresh_ui()
            return
        p = Path(path)
        if p.exists() and not p.is_dir():
            self._gen_json_box_temp_msg = f"{p} is not a directory."
            logger.info(self._gen_json_box_temp_msg)
            self.refresh_ui()
            return

        indices_text = self.generate_indices_input.value.strip()
        if indices_text == "":
            indices = [1,]
        else:
            try:
                indices_text = indices_text.strip()
                if indices_text == "":
                    indices = [1,]
                if "-" in indices_text:
                    a, b = indices_text.split("-", 1)
                    indices = list(range(int(a), int(b) + 1))
                else:
                    indices = [int(p.strip()) for p in indices_text.split(",") if p.strip()]
            except Exception as e:
                self._gen_json_box_temp_msg = f"Failed to parse indices: {e}"
                logger.error(self._gen_json_box_temp_msg)
                self.refresh_ui()
                return
        try:
            _generate_config_json(self.experiment.config_file, indices, p)
            self._gen_json_box_temp_msg = f"Generated json for with ppids {indices}"
            logger.info(self._gen_json_box_temp_msg)
        except Exception as e:
            self._gen_json_box_temp_msg = f"Generation failed: {e}"
            logger.error(self._gen_json_box_temp_msg)
        self.refresh_ui()

    def edit_config(self):
        edit_btn = self.query_one("#btn_edit_config", Button)
        save_btn = self.query_one("#btn_save_config", Button)
        edit_btn.disabled = True
        save_btn.disabled = False
        self.config_edit_text.read_only = False
        self.refresh_ui()

    def save_config(self):
        edit_btn = self.query_one("#btn_edit_config", Button)
        save_btn = self.query_one("#btn_save_config", Button)
        edit_btn.disabled = False
        save_btn.disabled = True
        self.config_edit_text.read_only = True
        with open(self.experiment.config_file, "w") as f:
            f.write(self.config_edit_text.text)
        self.refresh_ui()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn_generate_advanced":
            self.create_config_advanced()
        elif bid == "btn_generate_simple":
            self.create_config_simple()
        elif bid == "btn_generate_json":
            self.generate_json()
        elif bid == "btn_edit_config":
            self.edit_config()
        elif bid == "btn_save_config":
            self.save_config()

    def refresh_ui(self):
        self.config_order_log.clear()
        if self.experiment is not None and self.experiment.config_file is not None:
            with open(self.experiment.config_file, "r") as f:
                self.config_edit_text.text = "".join(f.readlines())

            try:
                order_table_out = _get_table_for_participants(self.experiment.config_file)
                order_table_out = tabulate(order_table_out, headers='firstrow', tablefmt='fancy_grid')
            except Exception as e:
                order_table_out = f"Failed to load {self.experiment.config_file}: `{e}`"
            self.config_order_log.write(order_table_out)

        if self.experiment is not None:
            out = ""
            if self._config_file_box_temp_msg is not None:
                out += f"({self._config_file_box_temp_msg})"
                self._config_file_box_temp_msg = None
            self.config_edit_message.update(out)

            out = ""
            if self._gen_box_temp_msg is not None:
                out += f"({self._gen_box_temp_msg})"
                self._gen_box_temp_msg = None
            self.gen_box_message.update(out)

            out = ""
            if self._new_box_temp_msg is not None:
                out += f"({self._new_box_temp_msg})"
                self._new_box_temp_msg = None
            self.new_box_message.update(out)

            out = ""
            if self._gen_json_box_temp_msg is not None:
                out += f"({self._gen_json_box_temp_msg})"
                self._gen_json_box_temp_msg = None
            self.gen_json_box_message.update(out)


class ExperimentTextualApp(App):
    def __init__(self, config_path: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_path = config_path
        self.config_file_box = Static("boooo", id="loaded_config_file_box")
        self.experiment = None
        self.participant_tab: Optional[ParticipantTab] = None
        self.config_tab: Optional[ConfigTab] = None
        self.log_view = RichLog(id="log_view", markup=True)
        self._config_file_box_temp_msg: str|None = None

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield Header()
        yield Footer()

        # Load experiment if provided
        if self.config_path:
            try:
                self.experiment = Experiment(self.config_path, 1)
            except Exception as e:
                # show a warning but continue with a DummyExperiment
                yield Static(f"Warning loading config {self.config_path}: {e}")
                sys.exit(1)
        else:
            sys.exit(1)

        start_server_in_current_ioloop(self.experiment)

        with Grid(id="top_grid"):
            yield Static("Loaded config file:")
            yield self.config_file_box
            yield Button("Load different Config file", id="btn_load_config")
            yield Button("Refresh", id="btn_refresh")
        with TabbedContent():
            with TabPane("Participant Management"):
                self.participant_tab = ParticipantTab(self.experiment)
                yield self.participant_tab
            with TabPane("Manage Config"):
                self.config_tab = ConfigTab(self.experiment)
                yield self.config_tab

        with Collapsible(title="Log:", id="log_group"):
            with VerticalGroup():
                yield self.log_view
        self.refresh_ui()

    def on_mount(self):
        # Remove default stderr sink so nothing is printed to the CLI
        logger.remove()
        # Get running loop to safely schedule writes from other threads
        loop = asyncio.get_running_loop()
        def textual_sink(message):
            # message is a Loguru Message object; str(message) is the formatted text
            loop.call_soon_threadsafe(self.log_view.write, str(message))
        # Add Textual sink (enqueue=True for thread safety)
        logger.add(textual_sink, enqueue=True)

    # def load_config(self, path: str) -> None:
    #     p = Path(path)
    #     if not p.exists():
    #         raise FileNotFoundError(path)
    #     self.experiment = Experiment(str(p), 1)
    #     if self.participant_tab:
    #         self.participant_tab.experiment = self.experiment
    #         self.participant_tab.refresh_ui()
    #     if self.config_tab:
    #         self.config_tab.cfg_path_input.value = str(p)

    def refresh_ui(self):
        if self.experiment is not None:
            out = str(self.experiment._config_file)
            if self._config_file_box_temp_msg is not None:
                out += f"  ({self._config_file_box_temp_msg})"
                self._config_file_box_temp_msg = None
            self.config_file_box.update(out)
        if self.participant_tab is not None:
            self.participant_tab.refresh_ui()
        if self.config_tab is not None:
            self.config_tab.refresh_ui()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn_load_config":
            self.load_config()
        elif bid == "btn_refresh":
            self.refresh_ui()

    def load_config(self, config_loaded_callback:Callable|None=None) -> None:
        def load_config_callback(path: Path | None) -> None:
            if path is not None and self.experiment is not None:
                try:
                    self.experiment.config_file = path
                    if config_loaded_callback is not None:
                        config_loaded_callback()
                except Exception as e:
                    self._config_file_box_temp_msg = f"failed to load {path}"
                    logger.error(f"Failed to load config {e}")
            self.refresh_ui()

        self.push_screen(LoadConfig(os.curdir), load_config_callback)

    def action_quit(self) -> None:
        self.exit()
