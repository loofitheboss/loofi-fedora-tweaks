"""
Agents Tab — GUI for managing autonomous system agents.
Part of v19.0 "Vanguard".

Provides:
- Agent dashboard (summary, active agents, recent activity)
- Agent list with enable/disable/run controls and notification toggles
- Goal-based agent creation wizard
- Agent detail view with settings and history
"""

import logging
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QTextEdit, QLineEdit, QCheckBox, QSpinBox,
    QMessageBox, QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from ui.base_tab import BaseTab
from ui.tab_utils import configure_top_tabs

logger = logging.getLogger(__name__)

# Module constants
REFRESH_INTERVAL_MS = 10000


class AgentsTab(BaseTab):
    """Tab for managing autonomous system agents."""

    def __init__(self):
        super().__init__()
        self._scheduler = None
        self._init_ui()
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_all)
        self._refresh_timer.start(REFRESH_INTERVAL_MS)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Sub-tabs
        tabs = QTabWidget()
        configure_top_tabs(tabs)
        tabs.addTab(self._build_dashboard_tab(), self.tr("Dashboard"))
        tabs.addTab(self._build_agents_tab(), self.tr("My Agents"))
        tabs.addTab(self._build_create_tab(), self.tr("Create Agent"))
        tabs.addTab(self._build_activity_tab(), self.tr("Activity Log"))
        layout.addWidget(tabs)

        # Output area
        self.add_output_section(layout)

    # ==================== Dashboard Sub-Tab ====================

    def _build_dashboard_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Summary cards
        cards = QGridLayout()

        self.lbl_total = self._make_stat_card("Total Agents", "0")
        self.lbl_enabled = self._make_stat_card("Enabled", "0")
        self.lbl_running = self._make_stat_card("Running", "0")
        self.lbl_errors = self._make_stat_card("Errors", "0")
        self.lbl_total_runs = self._make_stat_card("Total Runs", "0")

        cards.addWidget(self.lbl_total, 0, 0)
        cards.addWidget(self.lbl_enabled, 0, 1)
        cards.addWidget(self.lbl_running, 0, 2)
        cards.addWidget(self.lbl_errors, 0, 3)
        cards.addWidget(self.lbl_total_runs, 0, 4)
        layout.addLayout(cards)

        # Scheduler controls
        sched_box = QGroupBox(self.tr("Agent Scheduler"))
        sched_layout = QHBoxLayout(sched_box)

        self.lbl_scheduler_status = QLabel(self.tr("Scheduler: Stopped"))
        sched_layout.addWidget(self.lbl_scheduler_status)
        sched_layout.addStretch()

        self.btn_start_scheduler = QPushButton(self.tr("Start Scheduler"))
        self.btn_start_scheduler.clicked.connect(self._start_scheduler)
        sched_layout.addWidget(self.btn_start_scheduler)

        self.btn_stop_scheduler = QPushButton(self.tr("Stop Scheduler"))
        self.btn_stop_scheduler.clicked.connect(self._stop_scheduler)
        self.btn_stop_scheduler.setEnabled(False)
        sched_layout.addWidget(self.btn_stop_scheduler)

        layout.addWidget(sched_box)

        # Recent activity preview
        activity_box = QGroupBox(self.tr("Recent Activity"))
        activity_layout = QVBoxLayout(activity_box)

        self.activity_preview = QTextEdit()
        self.activity_preview.setReadOnly(True)
        self.activity_preview.setMaximumHeight(200)
        activity_layout.addWidget(self.activity_preview)

        layout.addWidget(activity_box)
        layout.addStretch()

        # Initial load
        QTimer.singleShot(100, self._refresh_dashboard)
        return widget

    def _make_stat_card(self, title: str, value: str) -> QGroupBox:
        box = QGroupBox()
        box.setFixedHeight(80)
        lay = QVBoxLayout(box)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        val_label = QLabel(value)
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        val_label.setFont(font)
        val_label.setObjectName(f"stat_{title.lower().replace(' ', '_')}")
        lay.addWidget(val_label)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title_label)

        box._value_label = val_label
        return box

    # ==================== My Agents Sub-Tab ====================

    def _build_agents_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Agent table
        self.agent_table = QTableWidget()
        self.agent_table.setColumnCount(8)
        self.agent_table.setHorizontalHeaderLabels([
            self.tr("Name"), self.tr("Type"), self.tr("Status"),
            self.tr("Runs"), self.tr("Last Run"), self.tr("Enabled"),
            self.tr("Notify"), self.tr("Actions"),
        ])
        header = self.agent_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.agent_table.setColumnWidth(7, 200)
        self.agent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.agent_table)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton(self.tr("Refresh"))
        btn_refresh.clicked.connect(self._refresh_agents_table)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        QTimer.singleShot(200, self._refresh_agents_table)
        return widget

    # ==================== Create Agent Sub-Tab ====================

    def _build_create_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Goal input
        goal_box = QGroupBox(self.tr("Create Agent from Goal"))
        goal_layout = QVBoxLayout(goal_box)

        goal_layout.addWidget(QLabel(self.tr(
            "Describe what you want your agent to do, or pick a template below:"
        )))

        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText(self.tr(
            "e.g., 'Keep my system healthy' or 'Watch for security threats'"
        ))
        goal_layout.addWidget(self.goal_input)

        # Template buttons
        template_layout = QHBoxLayout()
        templates = [
            ("🏥 Health Monitor", "Keep my system healthy"),
            ("🛡️ Security Guard", "Watch for security threats"),
            ("📦 Update Watcher", "Notify me about updates"),
            ("🧹 Auto Cleanup", "Automatically clean up my system"),
            ("⚡ Performance", "Optimize system performance automatically"),
        ]
        for label, goal in templates:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, g=goal: self.goal_input.setText(g))
            template_layout.addWidget(btn)
        goal_layout.addLayout(template_layout)

        btn_plan = QPushButton(self.tr("🤖 Generate Agent Plan"))
        btn_plan.clicked.connect(self._generate_plan)
        goal_layout.addWidget(btn_plan)

        layout.addWidget(goal_box)

        # Plan preview
        plan_box = QGroupBox(self.tr("Generated Plan"))
        plan_layout = QVBoxLayout(plan_box)

        self.plan_preview = QTextEdit()
        self.plan_preview.setReadOnly(True)
        self.plan_preview.setMaximumHeight(200)
        plan_layout.addWidget(self.plan_preview)

        # Plan options
        opts_layout = QGridLayout()

        opts_layout.addWidget(QLabel(self.tr("Dry Run (safe mode):")), 0, 0)
        self.chk_dry_run = QCheckBox()
        self.chk_dry_run.setChecked(True)
        opts_layout.addWidget(self.chk_dry_run, 0, 1)

        opts_layout.addWidget(QLabel(self.tr("Max actions per hour:")), 1, 0)
        self.spn_max_actions = QSpinBox()
        self.spn_max_actions.setRange(1, 100)
        self.spn_max_actions.setValue(10)
        opts_layout.addWidget(self.spn_max_actions, 1, 1)

        plan_layout.addLayout(opts_layout)

        btn_create = QPushButton(self.tr("✅ Create Agent"))
        btn_create.clicked.connect(self._create_agent_from_plan)
        plan_layout.addWidget(btn_create)

        layout.addWidget(plan_box)
        layout.addStretch()
        return widget

    # ==================== Activity Log Sub-Tab ====================

    def _build_activity_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(5)
        self.activity_table.setHorizontalHeaderLabels([
            self.tr("Time"), self.tr("Agent"), self.tr("Action"),
            self.tr("Result"), self.tr("Message"),
        ])
        header = self.activity_table.horizontalHeader()
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.activity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.activity_table)

        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton(self.tr("Refresh"))
        btn_refresh.clicked.connect(self._refresh_activity_table)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        QTimer.singleShot(300, self._refresh_activity_table)
        return widget

    # ==================== Actions ====================

    def _get_registry(self):
        from utils.agents import AgentRegistry
        return AgentRegistry.instance()

    def _get_scheduler(self):
        if self._scheduler is None:
            from utils.agent_runner import AgentScheduler
            self._scheduler = AgentScheduler()
            self._scheduler.set_result_callback(self._on_agent_result)
        return self._scheduler

    def _on_agent_result(self, agent_id: str, result):
        """Callback when an agent produces a result."""
        self.append_output(f"[{agent_id}] {result.message}\n")

    def _start_scheduler(self):
        scheduler = self._get_scheduler()
        scheduler.start()
        self.lbl_scheduler_status.setText(self.tr("Scheduler: Running"))
        self.btn_start_scheduler.setEnabled(False)
        self.btn_stop_scheduler.setEnabled(True)
        self.append_output(self.tr("Agent scheduler started\n"))

    def _stop_scheduler(self):
        scheduler = self._get_scheduler()
        scheduler.stop()
        self.lbl_scheduler_status.setText(self.tr("Scheduler: Stopped"))
        self.btn_start_scheduler.setEnabled(True)
        self.btn_stop_scheduler.setEnabled(False)
        self.append_output(self.tr("Agent scheduler stopped\n"))

    def _refresh_all(self):
        """Periodic refresh of all data."""
        try:
            self._refresh_dashboard()
        except Exception as exc:
            logger.debug("Dashboard refresh failed: %s", exc)

    def _refresh_dashboard(self):
        registry = self._get_registry()
        summary = registry.get_agent_summary()

        self.lbl_total._value_label.setText(str(summary["total_agents"]))
        self.lbl_enabled._value_label.setText(str(summary["enabled"]))
        self.lbl_running._value_label.setText(str(summary["running"]))
        self.lbl_errors._value_label.setText(str(summary["errors"]))
        self.lbl_total_runs._value_label.setText(str(summary["total_runs"]))

        # Activity preview
        activity = registry.get_recent_activity(limit=10)
        lines = []
        for item in activity:
            ts = time.strftime("%H:%M:%S", time.localtime(item["timestamp"]))
            icon = "✅" if item["success"] else "❌"
            lines.append(f"{ts} {icon} [{item['agent_name']}] {item['message']}")
        self.activity_preview.setPlainText("\n".join(lines) if lines else self.tr("No recent activity"))

    def _refresh_agents_table(self):
        registry = self._get_registry()
        agents = registry.list_agents()

        self.agent_table.setRowCount(len(agents))
        for row, agent in enumerate(agents):
            state = registry.get_state(agent.agent_id)

            self.agent_table.setItem(row, 0, QTableWidgetItem(agent.name))
            self.agent_table.setItem(row, 1, QTableWidgetItem(agent.agent_type.value))

            status_item = QTableWidgetItem(state.status.value)
            if state.status.value == "running":
                status_item.setForeground(Qt.GlobalColor.green)
            elif state.status.value == "error":
                status_item.setForeground(Qt.GlobalColor.red)
            self.agent_table.setItem(row, 2, status_item)

            self.agent_table.setItem(row, 3, QTableWidgetItem(str(state.run_count)))

            last_run = ""
            if state.last_run:
                last_run = time.strftime("%Y-%m-%d %H:%M", time.localtime(state.last_run))
            self.agent_table.setItem(row, 4, QTableWidgetItem(last_run))

            self.agent_table.setItem(
                row, 5, QTableWidgetItem("✅" if agent.enabled else "❌")
            )

            # Notification status
            notif_enabled = agent.notification_config.get("enabled", False)
            self.agent_table.setItem(
                row, 6, QTableWidgetItem("🔔" if notif_enabled else "🔕")
            )

            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)

            btn_toggle = QPushButton(self.tr("Disable") if agent.enabled else self.tr("Enable"))
            btn_toggle.clicked.connect(
                lambda checked, aid=agent.agent_id, en=agent.enabled: self._toggle_agent(aid, en)
            )
            actions_layout.addWidget(btn_toggle)

            btn_run = QPushButton(self.tr("Run"))
            btn_run.clicked.connect(
                lambda checked, aid=agent.agent_id: self._run_agent_now(aid)
            )
            actions_layout.addWidget(btn_run)

            btn_notify = QPushButton(self.tr("🔕") if notif_enabled else self.tr("🔔"))
            btn_notify.setToolTip(self.tr("Toggle notifications"))
            btn_notify.clicked.connect(
                lambda checked, aid=agent.agent_id, ne=notif_enabled: self._toggle_notifications(aid, ne)
            )
            actions_layout.addWidget(btn_notify)

            self.agent_table.setCellWidget(row, 7, actions_widget)

    def _toggle_agent(self, agent_id: str, currently_enabled: bool):
        registry = self._get_registry()
        if currently_enabled:
            registry.disable_agent(agent_id)
            self.append_output(self.tr("Agent disabled: {}\n").format(agent_id))
        else:
            registry.enable_agent(agent_id)
            self.append_output(self.tr("Agent enabled: {}\n").format(agent_id))
        self._refresh_agents_table()
        self._refresh_dashboard()

    def _run_agent_now(self, agent_id: str):
        scheduler = self._get_scheduler()
        self.append_output(self.tr("Running agent {} now...\n").format(agent_id))
        results = scheduler.run_agent_now(agent_id)
        for r in results:
            icon = "✅" if r.success else "❌"
            self.append_output(f"  {icon} {r.message}\n")
        self._refresh_agents_table()
        self._refresh_dashboard()

    def _generate_plan(self):
        goal = self.goal_input.text().strip()
        if not goal:
            QMessageBox.warning(
                self, self.tr("No Goal"),
                self.tr("Please enter a goal or select a template.")
            )
            return

        from utils.agent_planner import AgentPlanner
        plan = AgentPlanner.plan_from_goal(goal)

        # Store for creation
        self._current_plan = plan

        # Display plan
        lines = [
            f"Agent: {plan.agent_name}",
            f"Type: {plan.agent_type.value}",
            f"Description: {plan.description}",
            f"Confidence: {plan.confidence:.0%}",
            f"Trigger: every {plan.trigger.config.get('seconds', 300)}s",
            "",
            "Steps:",
        ]
        for step in plan.steps:
            lines.append(f"  {step.step_number}. {step.description} ({step.operation})")

        if plan.settings:
            lines.append("")
            lines.append("Settings:")
            for k, v in plan.settings.items():
                lines.append(f"  {k}: {v}")

        self.plan_preview.setPlainText("\n".join(lines))

    def _create_agent_from_plan(self):
        if not hasattr(self, "_current_plan") or self._current_plan is None:
            QMessageBox.warning(
                self, self.tr("No Plan"),
                self.tr("Generate a plan first using the Goal input above.")
            )
            return

        plan = self._current_plan
        config = plan.to_agent_config()
        config.dry_run = self.chk_dry_run.isChecked()
        config.max_actions_per_hour = self.spn_max_actions.value()

        registry = self._get_registry()
        registered = registry.register_agent(config)

        self.append_output(
            self.tr("✅ Agent '{}' created (ID: {})\n").format(
                registered.name, registered.agent_id
            )
        )
        self._current_plan = None
        self.plan_preview.clear()
        self.goal_input.clear()
        self._refresh_agents_table()
        self._refresh_dashboard()

    def _refresh_activity_table(self):
        registry = self._get_registry()
        activity = registry.get_recent_activity(limit=50)

        self.activity_table.setRowCount(len(activity))
        for row, item in enumerate(activity):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item["timestamp"]))
            self.activity_table.setItem(row, 0, QTableWidgetItem(ts))
            self.activity_table.setItem(row, 1, QTableWidgetItem(item["agent_name"]))
            self.activity_table.setItem(row, 2, QTableWidgetItem(item["action_id"]))

            result_item = QTableWidgetItem("✅" if item["success"] else "❌")
            self.activity_table.setItem(row, 3, result_item)

            self.activity_table.setItem(row, 4, QTableWidgetItem(item["message"][:100]))

    def _toggle_notifications(self, agent_id: str, currently_enabled: bool):
        """Toggle notification config for an agent."""
        registry = self._get_registry()
        agent = registry.get_agent(agent_id)
        if not agent:
            return
        if currently_enabled:
            agent.notification_config["enabled"] = False
            self.append_output(self.tr("Notifications disabled for {}\n").format(agent_id))
        else:
            agent.notification_config["enabled"] = True
            self.append_output(self.tr("Notifications enabled for {}\n").format(agent_id))
        registry.save()
        self._refresh_agents_table()

    def cleanup(self):
        """Stop timer and scheduler — called on application exit."""
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()
        if self._scheduler is not None and self._scheduler.is_running:
            self._scheduler.stop()
