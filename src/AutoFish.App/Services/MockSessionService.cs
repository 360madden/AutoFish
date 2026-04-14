using AutoFish.Contracts.Models;
using AutoFish.App.Profiles;

namespace AutoFish.App.Services;

public sealed class MockSessionService : ISessionService
{
    private readonly IProfileCatalog _profileCatalog;
    private readonly Random _random = new(7);
    private readonly List<string> _bridgeLog = new();

    private ControllerMode _mode = ControllerMode.Idle;
    private string _activeProfileId;
    private string _lastAction = "bootstrap";
    private string _lastReason = "desktop app initialized with mock session service";
    private int _casts;
    private int _hooksets;
    private int _catches;
    private int _skillUps;
    private int _recoveries;
    private int _maintenanceActions;
    private int _remainingBait = 20;
    private int _freeSlots = 12;
    private int _tick;

    public MockSessionService(IProfileCatalog profileCatalog, string? initialProfileId = null)
    {
        _profileCatalog = profileCatalog;
        _activeProfileId = ResolveInitialProfileId(initialProfileId);
        _bridgeLog.Add($"{DateTimeOffset.Now:HH:mm:ss} mock bridge online");
    }

    public IReadOnlyList<FishingProfile> Profiles => _profileCatalog.GetAll();

    public FishingProfile GetProfile(string id) => _profileCatalog.GetById(id);

    public SessionStatus GetSnapshot()
    {
        Advance();
        var profile = GetProfile(_activeProfileId);

        var alerts = new List<string>();
        if (_remainingBait <= profile.Thresholds.RebaitAtOrBelow)
        {
            alerts.Add("Bait low - schedule a maintenance action soon.");
        }

        if (_freeSlots <= profile.Thresholds.MaintenanceAtFreeSlotsOrBelow)
        {
            alerts.Add("Inventory nearly full - prepare maintenance/vendoring.");
        }

        if (_mode == ControllerMode.Paused)
        {
            alerts.Add("Controller is paused by operator or safety rule.");
        }

        return new SessionStatus(
            CharacterName: "OfflineOperator",
            ActiveProfile: _activeProfileId,
            Mode: _mode,
            InGame: true,
            NearWater: _mode is not ControllerMode.Idle,
            InCombat: false,
            InventoryFull: _freeSlots <= 0,
            BridgeOnline: true,
            RemainingBait: _remainingBait,
            FreeSlots: _freeSlots,
            LastAction: _lastAction,
            LastReason: _lastReason,
            UpdatedAtUtc: DateTimeOffset.UtcNow,
            Counters: new SessionCounters(_casts, _hooksets, _catches, _skillUps, _recoveries, _maintenanceActions),
            Alerts: alerts);
    }

    public IReadOnlyList<string> GetBridgeLog() => _bridgeLog.ToArray();

    public void SendCommand(BridgeCommand command)
    {
        switch (command.CommandType)
        {
            case BridgeCommandType.Start:
                _mode = ControllerMode.Scanning;
                _lastAction = "start";
                _lastReason = "operator started the session";
                break;
            case BridgeCommandType.Pause:
                _mode = ControllerMode.Paused;
                _lastAction = "pause";
                _lastReason = "operator paused the session";
                break;
            case BridgeCommandType.Resume:
                _mode = ControllerMode.Scanning;
                _lastAction = "resume";
                _lastReason = "operator resumed the session";
                break;
            case BridgeCommandType.Stop:
                _mode = ControllerMode.Idle;
                _lastAction = "stop";
                _lastReason = "operator stopped the session";
                break;
            case BridgeCommandType.SyncProfile:
                if (!string.IsNullOrWhiteSpace(command.ProfileId))
                {
                    _activeProfileId = GetProfile(command.ProfileId).Id;
                }

                _lastAction = "sync_profile";
                _lastReason = $"profile synchronized to {GetProfile(_activeProfileId).DisplayName}";
                break;
            case BridgeCommandType.RequestSnapshot:
                _lastAction = "request_snapshot";
                _lastReason = "operator requested an immediate session refresh";
                break;
            case BridgeCommandType.Ack:
                _lastAction = "ack";
                _lastReason = "bridge acknowledgement received";
                break;
        }

        _bridgeLog.Add($"{DateTimeOffset.Now:HH:mm:ss} {command.CommandType} ({command.ProfileId ?? _activeProfileId})");
        TrimLog();
    }

    private void Advance()
    {
        var profile = GetProfile(_activeProfileId);

        if (_mode is ControllerMode.Idle or ControllerMode.Paused)
        {
            return;
        }

        _tick++;
        var phase = _tick % 5;

        switch (phase)
        {
            case 0:
                _mode = ControllerMode.Scanning;
                _lastAction = "scan";
                _lastReason = "watching for bobber and bite signals";
                break;
            case 1:
                _mode = ControllerMode.Casting;
                _casts++;
                _remainingBait = Math.Max(0, _remainingBait - 1);
                _lastAction = "cast_line";
                _lastReason = "profile is ready for another cast";
                break;
            case 2:
                _mode = ControllerMode.WaitingBite;
                _lastAction = "wait_bite";
                _lastReason = "line is cast and waiting for a bite";
                break;
            case 3:
                _mode = ControllerMode.Hooking;
                _hooksets++;
                _lastAction = "set_hook";
                _lastReason = "bite detected by the local controller";
                break;
            default:
                _mode = ControllerMode.Looting;
                _catches++;
                _freeSlots = Math.Max(0, _freeSlots - 1);
                if (_catches % 3 == 0)
                {
                    _skillUps++;
                }

                _lastAction = "loot";
                _lastReason = "catch resolved and loot collected";
                break;
        }

        if (_remainingBait == 0)
        {
            _mode = ControllerMode.Maintenance;
            _maintenanceActions++;
            _remainingBait = 20;
            _lastAction = "rebait";
            _lastReason = "bait depleted; maintenance routine simulated";
        }

        if (_freeSlots == 0)
        {
            _mode = ControllerMode.Maintenance;
            _maintenanceActions++;
            _freeSlots = 12;
            _lastAction = "vendor_cleanup";
            _lastReason = "inventory full; cleanup routine simulated";
        }

        if (profile.Guardrails.RecoverOnDrift && _random.NextDouble() < 0.03)
        {
            _mode = ControllerMode.Recovering;
            _recoveries++;
            _lastAction = "recover_position";
            _lastReason = "temporary drift detected in mock session";
        }
    }

    private void TrimLog()
    {
        if (_bridgeLog.Count <= 50)
        {
            return;
        }

        _bridgeLog.RemoveRange(0, _bridgeLog.Count - 50);
    }

    private string ResolveInitialProfileId(string? initialProfileId)
    {
        if (!string.IsNullOrWhiteSpace(initialProfileId))
        {
            try
            {
                return GetProfile(initialProfileId).Id;
            }
            catch (KeyNotFoundException)
            {
            }
        }

        return _profileCatalog.GetAll()[0].Id;
    }
}
