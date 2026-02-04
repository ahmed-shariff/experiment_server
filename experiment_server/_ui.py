"""
Textual UI for experiment_server

Usage:
    python -m experiment_server._ui --config path/to/config.toml
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import click

from textual.app import App
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll,HorizontalGroup, VerticalGroup
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
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
    Switch
)
from experiment_server._api import Experiment
import toml  # type: ignore


def pretty_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


class ParticipantTab(Vertical):
    """Participant management tab."""
    def __init__(self, experiment:Experiment):
        super().__init__()
        self.experiment = experiment

        # Widgets
        self.status_box = Static(id="status_box")
        self.block_input = Input(placeholder="block id", id="block_input")
        self.block_all_input = Input(placeholder="block id (for all)", id="block_all_input")
        self.participants_table = DataTable(id="participants_table")
        self.config_pretty = Pretty("", id="config_pretty")

        self.monitor_default_switch = Switch(value=True)
        self.monitor_input = Input(placeholder="participant id (empty = default)", id="monitor_input", disabled=True)
        self.participant_id_to_add_input = Input(placeholder="participant id", id="participant_id_to_add_input")
        self.edit_container = Grid(id="edit_container")
        self.log_view = RichLog(id="log_view")

        self.participants_table.add_column("participant_id")
        self.participants_table.add_column("block_id")
        self.participants_table.add_column("block_name")
        self.participants_table.add_column("active")

        # editable inputs map when editing config
        self._edit_inputs: Dict[str, Input] = {}

    def compose(self):
        with VerticalScroll():
            with Collapsible(title="Current block config:", id="collapse_status", collapsed=False):
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
                    yield Button("Edit config", id="btn_edit_config")
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

        with Collapsible(title="Log:", id="log_group"):
            with VerticalGroup():
                yield self.log_view
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
            self.log_view.write(f"Moved to next block: {name}")
        except Exception as e:
            self.log_view.write(f"Error moving to next: {e}")
        self.refresh_ui()

    def move_to_block(self) -> None:
        pid = self._monitored_pid()
        v = self.block_input.value.strip()
        try:
            bid = int(v)
        except Exception:
            self.log_view.write("Invalid block id")
            return
        try:
            name = self.experiment.move_to_block(bid, pid)
            self.log_view.write(f"Moved participant {pid or 'default'} to block {bid} ({name})")
        except Exception as e:
            self.log_view.write(f"Error moving to block: {e}")
        self.refresh_ui()

    def reset_participant(self) -> None:
        pid = self._monitored_pid()
        try:
            self.experiment.reset_participant(pid)
            self.log_view.write(f"Reset participant {pid or 'default'}")
        except Exception as e:
            self.log_view.write(f"Error resetting participant: {e}")
        self.refresh_ui()

    def list_participants(self) -> None:
        try:
            self.participants_table.clear()
            for idx, st in sorted(self.experiment.global_state.items()):
                self.participants_table.add_row(str(idx), str(st.block_id), str(st.block_name), str(st.active))
            self.log_view.write("Listed participants")
        except Exception as e:
            self.log_view.write(f"Error listing participants: {e}")

    def move_all_to_block(self) -> None:
        v = self.block_all_input.value.strip()
        try:
            bid = int(v)
        except Exception:
            self.log_view.write("Invalid block id")
            return
        try:
            name = self.experiment.move_all_to_block(bid)
            self.log_view.write(f"Moved all participants to block {bid} ({name})")
        except Exception as e:
            self.log_view.write(f"Error moving all: {e}")
        self.refresh_ui()

    def set_monitor(self) -> None:
        pid = self._monitored_pid()
        if pid is None:
            self.log_view.write("Monitoring default participant")
        else:
            if pid not in getattr(self.experiment, "global_state", {}):
                self.log_view.write(f"Participant {pid} not known. Use New participant to add.")
            else:
                self.log_view.write(f"Now monitoring participant {pid}")
        self.refresh_ui()

    def new_participant(self) -> None:
        try:
            new_id = self.experiment.get_next_participant()
            self.log_view.write(f"Created new participant {new_id}")
        except Exception as e:
            self.log_view.write(f"Error creating participant: {e}")
        self.refresh_ui()

    def new_participant_with_id(self) -> None:
        v = self.participant_id_to_add_input.value.strip()
        try:
            id = int(v)
        except Exception:
            self.log_view.write("Invalid participant id")
            return
        try:
            new_id = self.experiment.add_participant_index(id)
            self.log_view.write(f"Created new participant {new_id}")
        except Exception as e:
            self.log_view.write(f"Error creating participant: {e}")
        self.refresh_ui()

    # Config editing
    def start_edit_config(self) -> None:
        pid = self._monitored_pid()
        try:
            cfg = self.experiment.get_config(pid)
        except Exception as e:
            self.log_view.write(f"Cannot edit config: {e}")
            return
        if cfg is None:
            self.log_view.write("Participant not active. Call Move to next first.")
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
        self.log_view.write("Mounted edit inputs. Fill values and press Submit edits.")

    def submit_edits(self) -> None:
        self.edit_container.remove_class("round_border")
        if not self._edit_inputs:
            self.log_view.write("No edits in progress.")
            return
        pid = self._monitored_pid()
        try:
            cfg = self.experiment.get_config(pid)
        except Exception as e:
            self.log_view.write(f"Cannot submit: {e}")
            return
        if cfg is None:
            self.log_view.write("Participant not active.")
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
                self.log_view.write(f"Failed parsing {k}: {e}")
                errors = True

        if not errors:
            self.log_view.write("Config updated in-memory.")
            for child in list(self.edit_container.children):
                child.remove()
            self._edit_inputs.clear()
        else:
            self.log_view.write("One or more fields failed to parse; fix and submit again.")
        self.refresh_ui()

    def cancel_edits(self) -> None:
        self.edit_container.remove_class("round_border")
        self._edit_inputs.clear()
        for child in list(self.edit_container.children):
            child.remove()
        self.log_view.write("Cancelled edits.")
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


class ConfigTab(Vertical):
    """Manage config tab."""

    def __init__(self, start_config_path: Optional[Path] = None):
        super().__init__()
        self.cfg_path_input = Input(placeholder="path to toml config file", id="cfg_path")
        if start_config_path:
            self.cfg_path_input.value = str(start_config_path)
        self.new_cfg_path = Input(placeholder="output toml path", id="new_cfg_path")
        self.order_input = Input(placeholder='order as JSON list, e.g. ["condA","condB"]', id="order_input")
        self.blocks_input = Input(placeholder='blocks as JSON list of block names', id="blocks_input")
        self.generate_indices_input = Input(placeholder="participant indices CSV or range (e.g. 1,2,3 or 1-5)", id="gen_indices")
        self.output = RichLog()

    def compose(self):
        yield Label("Create / Verify / Generate Config")
        yield Horizontal(Label("Existing config:"), self.cfg_path_input, Button("Verify", id="btn_verify"), Button("Generate JSON", id="btn_generate"))
        yield Static("--- Create new minimal config ---")
        yield Horizontal(self.new_cfg_path, Button("Create", id="btn_create"))
        yield Label("Order (JSON list):")
        yield self.order_input
        yield Label("Blocks (JSON list of block names):")
        yield self.blocks_input
        yield Label("Participant indices (CSV or range) for generation:")
        yield self.generate_indices_input
        yield self.output

    def _parse_indices(self, s: str) -> List[int]:
        s = s.strip()
        if s == "":
            return []
        if "-" in s:
            a, b = s.split("-", 1)
            return list(range(int(a), int(b) + 1))
        return [int(p.strip()) for p in s.split(",") if p.strip()]

    def create_config(self) -> None:
        outp = self.new_cfg_path.value.strip()
        if outp == "":
            self.output.write("Provide output TOML path.")
            return
        try:
            order_val = json.loads(self.order_input.value) if self.order_input.value.strip() else [["conditionA", "conditionB"]]
            blocks_val = json.loads(self.blocks_input.value) if self.blocks_input.value.strip() else ["conditionA", "conditionB"]
        except Exception as e:
            self.output.write(f"Failed to parse JSON fields: {e}")
            return
        minimal = {"configuration": {"order": order_val}, "blocks": []}
        for name in blocks_val:
            minimal["blocks"].append({"name": name, "config": {}})
        p = Path(outp)
        try:
            if toml:
                with p.open("w", encoding="utf-8") as f:
                    toml.dump(minimal, f)
            else:
                lines = []
                lines.append("[configuration]")
                lines.append(f'order = {json.dumps(order_val)}')
                for b in minimal["blocks"]:
                    lines.append("")
                    lines.append('[[blocks]]')
                    lines.append(f'name = "{b["name"]}"')
                    lines.append("[blocks.config]")
                p.write_text("\n".join(lines), encoding="utf-8")
            self.output.write(f"Wrote config to {p}")
        except Exception as e:
            self.output.write(f"Failed to write config: {e}")

    def verify_config(self) -> None:
        path = self.cfg_path_input.value.strip()
        if not path:
            self.output.write("Provide path to config to verify.")
            return
        p = Path(path)
        if not p.exists():
            self.output.write("File not found.")
            return
        try:
            exp = Experiment(str(p), 1)
            cnt = exp.get_blocks_count(None)
            self.output.write(f"Config loaded OK. Blocks count: {cnt}")
            configs = exp.get_all_configs(1)
            if configs:
                self.output.write("Participant 1 first block config:")
                self.output.write(pretty_json(configs[0]))
        except Exception as e:
            self.output.write(f"Verification failed: {e}")

    def generate_json(self) -> None:
        path = self.cfg_path_input.value.strip()
        if not path:
            self.output.write("Provide path to config to generate from.")
            return
        p = Path(path)
        if not p.exists():
            self.output.write("File not found.")
            return
        indices_text = self.generate_indices_input.value.strip()
        if indices_text == "":
            indices = [1]
        else:
            try:
                indices = self._parse_indices(indices_text)
            except Exception as e:
                self.output.write(f"Failed to parse indices: {e}")
                return
        try:
            exp = Experiment(str(p), 1)
            for idx in indices:
                configs = exp.get_all_configs(idx)
                out_name = p.with_suffix(f".participant_{idx}.json")
                out_name.write_text(pretty_json(configs), encoding="utf-8")
                self.output.write(f"Wrote {out_name}")
        except Exception as e:
            self.output.write(f"Generation failed: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn_create":
            self.create_config()
        elif bid == "btn_verify":
            self.verify_config()
        elif bid == "btn_generate":
            self.generate_json()


class ExperimentTextualApp(App):
    def __init__(self, config_path: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_path = config_path
        self.experiment = None
        self.participant_tab: Optional[ParticipantTab] = None
        self.config_tab: Optional[ConfigTab] = None

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
                yield Static(f"Warning loading config {self.config_path}: {e}", style="bold red")
                sys.exit(1)
        else:
            sys.exit(1)

        with TabbedContent():
            with TabPane("Participant Management"):
                yield ParticipantTab(self.experiment)
            with TabPane("Manage Config"):
                yield ConfigTab(start_config_path=Path(self.config_path) if self.config_path else None)

    def load_config(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)
        self.experiment = Experiment(str(p), 1)
        if self.participant_tab:
            self.participant_tab.experiment = self.experiment
            self.participant_tab.refresh_ui()
        if self.config_tab:
            self.config_tab.cfg_path_input.value = str(p)

    def action_quit(self) -> None:
        self.exit()
