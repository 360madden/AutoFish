using AutoFish.App.Settings;
using AutoFish.App.Services;
using AutoFish.Contracts.Models;

namespace AutoFish.App;

public sealed class MainForm : Form
{
    private readonly ISessionService _sessionService;
    private readonly IHelperSettingsStore _settingsStore;
    private readonly System.Windows.Forms.Timer _pollTimer;
    private readonly ComboBox _profileCombo = new() { Dock = DockStyle.Top, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly NumericUpDown _refreshIntervalInput = new() { Minimum = 250, Maximum = 5000, Increment = 250, Width = 90 };
    private readonly Label _modeValue = BuildValueLabel();
    private readonly Label _characterValue = BuildValueLabel();
    private readonly Label _profileValue = BuildValueLabel();
    private readonly Label _baitValue = BuildValueLabel();
    private readonly Label _freeSlotsValue = BuildValueLabel();
    private readonly Label _lastActionValue = BuildValueLabel();
    private readonly Label _lastReasonValue = BuildValueLabel();
    private readonly Label _bridgeValue = BuildValueLabel();
    private readonly Label _countersValue = BuildValueLabel();
    private readonly ListBox _alertsList = new() { Dock = DockStyle.Fill };
    private readonly TextBox _bridgeLog = new() { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill };
    private readonly TextBox _architectureText = new() { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill };
    private readonly TextBox _profileDetailsText = new() { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill };
    private readonly StatusStrip _statusStrip = new();
    private readonly ToolStripStatusLabel _selectedProfileStatus = new();
    private readonly ToolStripStatusLabel _activeProfileStatus = new();
    private readonly ToolStripStatusLabel _refreshStatus = new();
    private readonly ToolStripStatusLabel _updatedStatus = new() { Spring = true, TextAlign = ContentAlignment.MiddleRight };
    private HelperSettings _settings;

    public MainForm(ISessionService sessionService, IHelperSettingsStore settingsStore, HelperSettings settings)
    {
        _sessionService = sessionService;
        _settingsStore = settingsStore;
        _settings = settings;
        _pollTimer = new System.Windows.Forms.Timer { Interval = NormalizeRefreshInterval(_settings.RefreshIntervalMs) };
        _pollTimer.Tick += (_, _) => RefreshSnapshot();
        _profileCombo.DisplayMember = nameof(FishingProfile.DisplayName);
        _profileCombo.ValueMember = nameof(FishingProfile.Id);
        _profileCombo.SelectedIndexChanged += (_, _) => OnSelectedProfileChanged();
        _refreshIntervalInput.ValueChanged += (_, _) => OnRefreshIntervalChanged();

        Text = "AutoFish Control Center (.NET 10)";
        MinimumSize = new Size(1100, 700);
        StartPosition = FormStartPosition.CenterScreen;

        BuildLayout();
        SeedProfiles();
        RefreshSnapshot();
        _pollTimer.Start();
    }

    private void BuildLayout()
    {
        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 2,
            RowCount = 1,
            Padding = new Padding(12),
        };
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 38));
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 62));

        root.Controls.Add(BuildLeftColumn(), 0, 0);
        root.Controls.Add(BuildRightColumn(), 1, 0);
        Controls.Add(root);
        Controls.Add(BuildStatusStrip());
    }

    private Control BuildLeftColumn()
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 4,
            ColumnCount = 1,
        };
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 190));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 220));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 150));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        panel.Controls.Add(BuildSessionGroup(), 0, 0);
        panel.Controls.Add(BuildControlGroup(), 0, 1);
        panel.Controls.Add(BuildCountersGroup(), 0, 2);
        panel.Controls.Add(BuildAlertsGroup(), 0, 3);
        return panel;
    }

    private Control BuildSessionGroup()
    {
        var group = new GroupBox { Text = "Session Overview", Dock = DockStyle.Fill };
        var layout = BuildKeyValueGrid();
        layout.Controls.Add(BuildKeyLabel("Mode"), 0, 0);
        layout.Controls.Add(_modeValue, 1, 0);
        layout.Controls.Add(BuildKeyLabel("Character"), 0, 1);
        layout.Controls.Add(_characterValue, 1, 1);
        layout.Controls.Add(BuildKeyLabel("Active Profile"), 0, 2);
        layout.Controls.Add(_profileValue, 1, 2);
        layout.Controls.Add(BuildKeyLabel("Remaining Bait"), 0, 3);
        layout.Controls.Add(_baitValue, 1, 3);
        layout.Controls.Add(BuildKeyLabel("Free Slots"), 0, 4);
        layout.Controls.Add(_freeSlotsValue, 1, 4);
        layout.Controls.Add(BuildKeyLabel("Bridge"), 0, 5);
        layout.Controls.Add(_bridgeValue, 1, 5);
        group.Controls.Add(layout);
        return group;
    }

    private Control BuildControlGroup()
    {
        var group = new GroupBox { Text = "Operator Controls", Dock = DockStyle.Fill };
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 5, ColumnCount = 1, Padding = new Padding(8) };
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 32));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 44));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 44));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 36));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        layout.Controls.Add(_profileCombo, 0, 0);

        var topButtons = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true };
        topButtons.Controls.Add(BuildCommandButton("Start", BridgeCommandType.Start));
        topButtons.Controls.Add(BuildCommandButton("Pause", BridgeCommandType.Pause));
        topButtons.Controls.Add(BuildCommandButton("Resume", BridgeCommandType.Resume));
        topButtons.Controls.Add(BuildCommandButton("Stop", BridgeCommandType.Stop));
        layout.Controls.Add(topButtons, 0, 1);

        var bottomButtons = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true };
        bottomButtons.Controls.Add(BuildCommandButton("Sync Profile", BridgeCommandType.SyncProfile));
        bottomButtons.Controls.Add(BuildCommandButton("Snapshot", BridgeCommandType.RequestSnapshot));
        layout.Controls.Add(bottomButtons, 0, 2);

        var refreshPanel = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true };
        refreshPanel.Controls.Add(new Label { Text = "Refresh (ms)", AutoSize = true, Padding = new Padding(0, 8, 6, 0) });
        _refreshIntervalInput.Value = NormalizeRefreshInterval(_settings.RefreshIntervalMs);
        refreshPanel.Controls.Add(_refreshIntervalInput);
        layout.Controls.Add(refreshPanel, 0, 3);

        var note = new Label
        {
            Dock = DockStyle.Fill,
            Text = "Desktop app owns supervision, profile sync, and bridge health. The Lua addon should still fail safe locally if this app disconnects.",
            AutoSize = false,
        };
        layout.Controls.Add(note, 0, 4);

        group.Controls.Add(layout);
        return group;
    }

    private Control BuildCountersGroup()
    {
        var group = new GroupBox { Text = "Counters", Dock = DockStyle.Fill };
        var layout = BuildKeyValueGrid();
        layout.Controls.Add(BuildKeyLabel("Totals"), 0, 0);
        layout.Controls.Add(_countersValue, 1, 0);
        layout.Controls.Add(BuildKeyLabel("Last Action"), 0, 1);
        layout.Controls.Add(_lastActionValue, 1, 1);
        layout.Controls.Add(BuildKeyLabel("Reason"), 0, 2);
        layout.Controls.Add(_lastReasonValue, 1, 2);
        group.Controls.Add(layout);
        return group;
    }

    private Control BuildAlertsGroup()
    {
        var group = new GroupBox { Text = "Alerts", Dock = DockStyle.Fill };
        group.Controls.Add(_alertsList);
        return group;
    }

    private Control BuildRightColumn()
    {
        var tabs = new TabControl { Dock = DockStyle.Fill };
        tabs.TabPages.Add(BuildBridgeLogTab());
        tabs.TabPages.Add(BuildProfileTab());
        tabs.TabPages.Add(BuildArchitectureTab());
        return tabs;
    }

    private TabPage BuildBridgeLogTab()
    {
        var tab = new TabPage("Bridge Log");
        tab.Controls.Add(_bridgeLog);
        return tab;
    }

    private TabPage BuildArchitectureTab()
    {
        _architectureText.Text = string.Join(Environment.NewLine,
        [
            "AutoFish hybrid stack:",
            "",
            "1. Lua in-game core: state machine, local safety, in-game GUI.",
            "2. .NET 10 desktop app: operator GUI, profiles, telemetry, bridge supervision.",
            "3. Shared contracts: command/status payloads for bridge evolution.",
            "",
            "Current desktop app uses mock data offline, which is intentional until the live Rift bridge is validated.",
        ]);

        var tab = new TabPage("Architecture");
        tab.Controls.Add(_architectureText);
        return tab;
    }

    private TabPage BuildProfileTab()
    {
        var tab = new TabPage("Profile");
        tab.Controls.Add(_profileDetailsText);
        return tab;
    }

    private Control BuildStatusStrip()
    {
        _statusStrip.Items.Add(_selectedProfileStatus);
        _statusStrip.Items.Add(new ToolStripStatusLabel { Text = " | " });
        _statusStrip.Items.Add(_activeProfileStatus);
        _statusStrip.Items.Add(new ToolStripStatusLabel { Text = " | " });
        _statusStrip.Items.Add(_refreshStatus);
        _statusStrip.Items.Add(_updatedStatus);
        return _statusStrip;
    }

    private void SeedProfiles()
    {
        foreach (var profile in _sessionService.Profiles)
        {
            _profileCombo.Items.Add(profile);
        }

        if (!string.IsNullOrWhiteSpace(_settings.LastSelectedProfileId))
        {
            SelectProfile(_settings.LastSelectedProfileId);
        }

        if (_profileCombo.SelectedItem is null && _profileCombo.Items.Count > 0)
        {
            _profileCombo.SelectedIndex = 0;
        }
    }

    private void RefreshSnapshot()
    {
        var snapshot = _sessionService.GetSnapshot();
        var profile = _sessionService.GetProfile(snapshot.ActiveProfile);
        _modeValue.Text = snapshot.Mode.ToString();
        _characterValue.Text = snapshot.CharacterName;
        _profileValue.Text = profile.DisplayName;
        _baitValue.Text = snapshot.RemainingBait.ToString();
        _freeSlotsValue.Text = snapshot.FreeSlots.ToString();
        _lastActionValue.Text = snapshot.LastAction;
        _lastReasonValue.Text = snapshot.LastReason;
        _bridgeValue.Text = snapshot.BridgeOnline ? "Online" : "Offline";
        _countersValue.Text = $"Casts={snapshot.Counters.Casts}, Hooksets={snapshot.Counters.Hooksets}, Catches={snapshot.Counters.Catches}, SkillUps={snapshot.Counters.SkillUps}, Recoveries={snapshot.Counters.Recoveries}, Maintenance={snapshot.Counters.MaintenanceActions}";

        _alertsList.BeginUpdate();
        _alertsList.Items.Clear();
        if (snapshot.Alerts.Count == 0)
        {
            _alertsList.Items.Add("No active alerts.");
        }
        else
        {
            foreach (var alert in snapshot.Alerts)
            {
                _alertsList.Items.Add(alert);
            }
        }
        _alertsList.EndUpdate();

        _bridgeLog.Lines = _sessionService.GetBridgeLog().ToArray();

        if (_profileCombo.SelectedItem is null)
        {
            SelectProfile(snapshot.ActiveProfile);
        }

        UpdateProfileDetails((_profileCombo.SelectedItem as FishingProfile)?.Id ?? snapshot.ActiveProfile);
        _selectedProfileStatus.Text = $"Selected: {(_profileCombo.SelectedItem as FishingProfile)?.DisplayName ?? "None"}";
        _activeProfileStatus.Text = $"Active: {profile.DisplayName}";
        _refreshStatus.Text = $"Refresh: {_pollTimer.Interval} ms";
        _updatedStatus.Text = $"Updated: {DateTime.Now:HH:mm:ss}";
    }

    private void SelectProfile(string profileId)
    {
        foreach (var item in _profileCombo.Items)
        {
            if (item is FishingProfile profile && string.Equals(profile.Id, profileId, StringComparison.OrdinalIgnoreCase))
            {
                _profileCombo.SelectedItem = item;
                return;
            }
        }

        if (_profileCombo.SelectedItem is null && _profileCombo.Items.Count > 0)
        {
            _profileCombo.SelectedIndex = 0;
        }
    }

    private void OnSelectedProfileChanged()
    {
        var selectedProfileId = (_profileCombo.SelectedItem as FishingProfile)?.Id;
        if (string.IsNullOrWhiteSpace(selectedProfileId))
        {
            return;
        }

        _settings = _settings with { LastSelectedProfileId = selectedProfileId };
        _settingsStore.Save(_settings);
        UpdateProfileDetails(selectedProfileId);
        _selectedProfileStatus.Text = $"Selected: {(_profileCombo.SelectedItem as FishingProfile)?.DisplayName ?? "None"}";
    }

    private void UpdateProfileDetails(string profileId)
    {
        var profile = _sessionService.GetProfile(profileId);
        _profileDetailsText.Text = string.Join(Environment.NewLine,
        [
            $"Display Name: {profile.DisplayName}",
            $"Id: {profile.Id}",
            $"Zone: {profile.ZoneName}",
            $"Target Skill: {profile.TargetSkill}",
            $"Enabled Skills: {string.Join(", ", profile.EnabledSkills)}",
            $"Bait: {profile.BaitName ?? "None"}",
            "",
            "Pacing",
            $"  Reaction: {profile.Pacing.ReactionFloorMs}-{profile.Pacing.ReactionCeilingMs} ms",
            $"  Bite Timeout: {profile.Pacing.BiteTimeoutMs} ms",
            $"  Loot Timeout: {profile.Pacing.LootTimeoutMs} ms",
            "",
            "Thresholds",
            $"  Rebait At Or Below: {profile.Thresholds.RebaitAtOrBelow}",
            $"  Maintenance At Free Slots Or Below: {profile.Thresholds.MaintenanceAtFreeSlotsOrBelow}",
            $"  Max Recovery Attempts: {profile.Thresholds.MaxRecoveryAttempts}",
            "",
            "Guardrails",
            $"  Pause On Combat: {profile.Guardrails.PauseOnCombat}",
            $"  Pause On Bridge Loss: {profile.Guardrails.PauseOnBridgeLoss}",
            $"  Recover On Drift: {profile.Guardrails.RecoverOnDrift}",
            "",
            "Notes",
            .. profile.Notes.Select(note => $"- {note}"),
        ]);
    }

    private void OnRefreshIntervalChanged()
    {
        var interval = NormalizeRefreshInterval((int)_refreshIntervalInput.Value);
        _pollTimer.Interval = interval;
        _settings = _settings with { RefreshIntervalMs = interval };
        _settingsStore.Save(_settings);
        _refreshStatus.Text = $"Refresh: {interval} ms";
    }

    private Button BuildCommandButton(string text, BridgeCommandType commandType)
    {
        var button = new Button { Text = text, AutoSize = true };
        button.Click += (_, _) =>
        {
            var selectedProfileId = (_profileCombo.SelectedItem as FishingProfile)?.Id;
            _sessionService.SendCommand(new BridgeCommand(
                commandType,
                DateTimeOffset.UtcNow,
                ProfileId: selectedProfileId,
                Notes: $"Issued from desktop GUI button: {text}"));

            RefreshSnapshot();
        };

        return button;
    }

    private static TableLayoutPanel BuildKeyValueGrid()
    {
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 6, Padding = new Padding(8) };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 120));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        for (var i = 0; i < 6; i++)
        {
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        }

        return layout;
    }

    private static Label BuildKeyLabel(string text) => new() { Text = text, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };

    private static Label BuildValueLabel() => new() { Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft, AutoEllipsis = true };

    private static int NormalizeRefreshInterval(int intervalMs) => Math.Clamp(intervalMs, 250, 5000);
}
