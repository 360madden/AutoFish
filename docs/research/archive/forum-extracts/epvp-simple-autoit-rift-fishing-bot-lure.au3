#include <Misc.au3>
#include <Date.au3>
#include <MsgBoxConstants.au3>
#include <WinAPI.au3>
#include <GUIConstantsEx.au3>
; ********************* IMPORTANT!!!!!!!! *************************
; This is set up to work with 'autoloot' set to 'off'.
; If you use Autoloot then once you catch something it automatically
; puts the fish in your back-pack.  However, there iis not any simple
; event to catch that the loot box has popped and has gone away - therefore
; you must set 'autoloot' to 'off' as follows:
;
;       SYSTEM -> Settings -> Interface -> Misc
;
; setting page and uncheck the box 'Auto-Loot By Default' then
; 'Apply' that change.
;
; *****************************************************************
Local $i, $j
Local $timer
Global $g_MouseX, $g_MouseY, $g_MouseCount, $g_MouseReposition
Global $g_timeLastLooted
Global $g_CsrNbr
Global $g_LastCrsNbr
Global $g_CastCount, $g_PullCount, $g_LootCount, $g_RecastCount
Global $g_XPixelOffset = 50 ; you may have to play with this value to work on resolutions other than 1920 x 1080
Global $g_YPixelOffset = 65 ; you may have to play with this value to work on resolutions other than 1920 x 1080
Global $g_UseLure = False
Global $g_RodPos[2]
Global $g_LurePos[2]
Global $g_LureDuration
Global $g_LureCooldown
Global $g_LureDurationTimer = 0
Global $g_LureCooldownTimer = 0
HotKeySet("{esc}","Terminate")

Setup()
While 1
	$g_CsrNbr = _WinAPI_GetCursorInfo()
	If $g_LastCrsNbr = $g_CsrNbr[2] Then
		; the cursor type has not changed, move the cursor a little bit since sometimes that masks the cursor change
		$g_MouseCount = $g_MouseCount+1
		If $g_MouseCount >= 5 Then
			$g_MouseCount = 0
			If $g_MouseReposition = True Then
				MouseMove($g_MouseX, $g_MouseY)
				$g_MouseReposition = False
			Else
				MouseMove($g_MouseX+Random(-2,2),$g_MouseY+Random(-2,2))
				$g_MouseReposition = True
			EndIf
		Endif
	Else
		; the cursor type changed, pull it in!
		FishingRodPull()
		; after the pull the loot popup may appear
		If isLoot() Then
			; the loot popup is now active
			LootFish()
			$g_RecastCount = 0
			$g_timeLastLooted=TimerInit()
			If $g_UseLure Then
				LureRefreshCheck()
			EndIf
			Cast()
		EndIf
	EndIf
	Sleep(100)
	;check if it has been more than 45 seconds since last successful catch
	If TimerDiff($g_TimeLastLooted) > 45000 Then
		$g_RecastCount =$g_RecastCount+1
		If $g_RecastCount < 10 Then
			ConsoleWrite(_NowTime(5)&" **** Recasting "&$g_RecastCount&@LF)
			$g_timeLastLooted=TimerInit()
			Cast()
		Else
			; 7.5 minutes without a catch, something is wrong, stop program
			Exit
		EndIf
	EndIf
WEnd

Func Setup()
	; see if a lure is desired
	$g_RodPos[0]=-1
	$g_RodPos[1]=-1
	$g_LurePos[0]=-1
	$g_LurePos[1]=-1
	GetLureInfo()
	If $g_UseLure Then
		ConsoleWrite("Rod: X="&$g_RodPos[0]&", Y="&$g_RodPos[1]&@LF)
		ConsoleWrite("Lure: X="&$g_LurePos[0]&", Y="&$g_LurePos[1]&@LF)
		ConsoleWrite("Duration:"&$g_LureDuration/1000/60&" minutes"&@LF)
		ConsoleWrite("Cooldown:"&$g_LureCooldown/1000/60/60&" hours"&@LF&@LF)
	Else
		ConsoleWrite("No lure selected"&@LF&@LF)
	EndIf
	Local $pos[2]
	ConsoleWrite(_NowTime(5)&" Initializing - you have 5 seconds to click on fishing area.  Must be at 1/2 screen or LOWER!"&@LF _
							&" Press 'ESC' to exit running program"&@LF _
				)
	Sleep(5000)
	$g_RecastCount=0
	$g_CastCount=0
	$g_PullCount=0
	$g_LootCount=0
	$pos=MouseGetPos()
	$g_MouseX=$pos[0]
	$g_MouseY=$pos[1]
	$g_timeLastLooted=TimerInit()
	If $g_UseLure Then
		LureRefreshCheck()
	EndIf
	MouseMove($g_MouseX,$g_MouseY)
	Cast()
EndFunc

Func IsLoot()
	Local $mousePos
	Local $oldPixelValue[20]
	Local $i, $x, $y
	Local $isLoot=True
	$mousePos = MouseGetPos()
	$x=$mousePos[0]-$g_XPixelOffset
	$y=$mousePos[1]-$g_YPixelOffset
	; get 20 pixels around and above where the cursor is located
	For $i=0 To 19
		$oldPixelValue[$i]=PixelGetColor($x+5*$i, $y)
	Next
	; wait for a short time
	Sleep(30)
	; if the loot popup is up then this area is constant and the screen does not change
	; if fishing then the water 'ripples' and at least one of these points will change
	For $i=0 To 19
		If $oldPixelValue[$i]<>PixelGetColor($x+5*$i, $y) Then
			; one of the pixels changed therefore loot popup is not up
			Return False
		EndIf
	Next
	; if it got here the loot popup is up
	Return True
EndFunc

Func Cast()
	$g_CastCount=$g_CastCount+1
	$g_PullCount=0
	ConsoleWrite(_NowTime(5)&" Casting "&$g_CastCount&@LF)
	MouseMove($g_MouseX,$g_MouseY)
	Sleep(100)
	MouseClick("left")
	Sleep(200)
	Send("1")
	Sleep(500)
	MouseClick("left")
	Sleep(500)
	$g_CsrNbr = _WinAPI_GetCursorInfo()
	$g_LastCrsNbr = $g_CsrNbr[2]
EndFunc

Func FishingRodPull()
	$g_PullCount=$g_PullCount+1
	ConsoleWrite(_NowTime(5)&" Pull    "&$g_CastCount&"."&$g_PullCount&@LF)
	Sleep(100)
	$pos= MouseGetPos()
	MouseClick("left", $pos[0], $pos[1], 1, 0)
	Sleep(500)
	$g_CsrNbr = _WinAPI_GetCursorInfo()
	$g_LastCrsNbr = $g_CsrNbr[2]
EndFunc

Func LootFish()
	$g_LootCount=$g_LootCount+1
	ConsoleWrite(_NowTime(5)&" Looting "&$g_LootCount&@LF)
	MouseClick("left")
	Sleep(200)
EndFunc

Func LureRefreshCheck()
	Local $cursorNbr
	Local $lastCrsNbr
	; check if the lure duration has exceeded]
	If $g_LureDuration < TimerDiff($g_LureDurationTimer) Then
		; see if the lure cooldown is over
		If $g_LureCooldown < TimerDiff($g_LureCooldownTimer) Then
			; time to apply the lure to the rod
			$lastCrsNbr = _WinAPI_GetCursorInfo()
			MouseMove($g_LurePos[0],$g_LurePos[1])
			Sleep(50)
			MouseClick("right")
			Sleep(100)
			$cursorNbr = _WinAPI_GetCursorInfo()
			If $cursorNbr[2] = $lastCrsNbr[2] Then
				; the cursor did not change, therefore there is no lure (probably used them all)
				ConsoleWrite(_NowTime(5)&" Could not apply lure - out of lures?"&@LF)
				$g_LureCooldown = 10^10 ; never check for this lure again
			Else
				; the cursor has changed and is ready to apply lure to rod
				MouseMove($g_RodPos[0],$g_RodPos[1])
				Sleep(50)
				MouseClick("left")
				; wait several seconds to allow lure to apply
				Sleep(5000)
				ConsoleWrite(_NowTime(5)&" Lure applied to rod"&@LF)
			EndIf
			; reset the timers
			$g_LureDurationTimer = TimerInit()
			$g_LureCooldownTimer = TimerInit()
		EndIf
	EndIf
EndFunc

Func GetLureInfo()
	; Create a GUI with various controls.
	Local $fishGui = GUICreate("Odlid Tubpu Fishing Bot", 550, 170, 200, 200)

	; Create a button control for exit and run the bot.
	Local $fishStartBtn = GUICtrlCreateButton("Start Fishing!", 210, 120, 100, 25)

	; Create a checkbox control for lure support
	Local $useLure = GUICtrlCreateCheckbox("Use a Lure?", 10, 10, 90, 25)
	Local $useLureText = GUICtrlCreateLabel("",100,16,450,25)
	; Create lure control labels
	Local $lureHeaderText = GUICtrlCreateLabel("Set Rod Position      Set Lure Position        Lure Duration           Lure Cooldown",76,40)
	GUICtrlSetColor($lureHeaderText, 0x808080)
	; Create a button control for rod position
	Local $rodPosBtn = GUICtrlCreateButton("Start", 70, 55, 90, 25)
	GUICtrlSetState($rodPosBtn, $GUI_DISABLE)
	GUICtrlSetTip($rodPosBtn, "Press the 'Start' button then LEFT click on your fishing rod in your OPEN BAG inventory")
	Local $rodPosText = GUICtrlCreateLabel("",76,85,90,25)
	; Create a button control for lure position
	Local $lureBtn = GUICtrlCreateButton("Start", 168, 55, 90, 25)
	GUICtrlSetState($lureBtn, $GUI_DISABLE)
	GUICtrlSetTip($lureBtn, "Press the 'Start' button then LEFT click on the stack of lures in your OPEN BAG inventory")
	Local $lurePosText = GUICtrlCreateLabel("",174,85,90,25)
	; Create dropdown for lure duration
	Local $lureDuration = GUICtrlCreateCombo("",266,56,90,25)
	GUICtrlSetState($lureDuration, $GUI_DISABLE)
	GUICtrlSetData($lureDuration, "2 minutes|5 minutes|10 minutes|15 minutes", "5 minutes")
	GUICtrlSetTip($lureDuration, "Set the duration this lure lasts on the rod")
	; Create dropdown for lure cooldown
	Local $lureCooldown = GUICtrlCreateCombo("",365,56,90,25)
	GUICtrlSetState($lureCooldown, $GUI_DISABLE)
	GUICtrlSetData($lureCooldown, "No Cooldown|2 hours|6 hours|8 hours", "No Cooldown")
	GUICtrlSetTip($lureCooldown, "Set the cooldown period for this lure before it can be applied again")

	; Create a
	; Display the GUI.
	GUISetState(@SW_SHOW, $fishGui)
	; Loop until the user exits.
	While 1
		Switch GUIGetMsg()
			Case $GUI_EVENT_CLOSE, $fishStartBtn
				; make sure everything is set up properly before exiting
				If $g_UseLure Then
					If $g_RodPos[0]<0 Or $g_RodPos[1]<0 Then
						MsgBox(0,"Error","Cannot exit, Lure requested but rod position is not set")
					ElseIf $g_LurePos[0]<0 Or $g_LurePos[1]<0 Then
						MsgBox(0,"Error","Cannot exit, Lure requested but rod position is not set")
					Else
						; all the lure stuff is set up properly
						$g_LureDuration = GUICtrlRead($lureDuration)
						$g_LureCooldown = GUICtrlRead($lureCooldown)
						Select
							; lures actually last 1 minute longer than they say
							Case $g_LureDuration = "2 minutes"
								$g_LureDuration  = 180000
							Case $g_LureDuration = "5 minutes"
								$g_LureDuration  = 360000
							Case $g_LureDuration = "10 minutes"
								$g_LureDuration  = 660000
							Case $g_LureDuration = "15 minutes"
								$g_LureDuration  = 960000
						EndSelect
						Select
							; add 2 mins to cooldown to be 'sure'
							Case $g_LureCooldown = "No Cooldown"
								$g_LureCooldown = 0
							Case $g_LureCooldown = "2 hour"
								$g_LureCooldown = 7380000
							Case $g_LureCooldown = "6 hours"
								$g_LureCooldown = 21780000
							Case $g_LureCooldown = "8 hours"
								$g_LureCooldown = 289800000
						EndSelect
						ExitLoop
					EndIf
				Else
					; no lure
					ExitLoop
				EndIf
			Case $useLure
				; only allow lure information when box is checked
                    If GUICtrlRead($useLure) = $GUI_CHECKED Then
					GUICtrlSetData($useLureText,"Your inventory bag(s) containing the rod and lure must BE OPEN and STAY OPEN to use lures!")
					GUICtrlSetColor($lureHeaderText, 0x000000)
					GUICtrlSetState($rodPosBtn, $GUI_Enable)
					GUICtrlSetState($lureBtn, $GUI_Enable)
					GUICtrlSetState($lureDuration, $GUI_Enable)
					GUICtrlSetState($lureCooldown, $GUI_Enable)
					If $g_RodPos[0] >= 0 Then
						GUICtrlSetData($rodPosText,"Set to ("&$g_RodPos[0]&","&$g_RodPos[1]&")")
					Else
						GUICtrlSetData($rodPosText,"")
					EndIf
					If $g_LurePos[0] >= 0 Then
						GUICtrlSetData($lurePosText,"X="&$g_LurePos[0]&" Y="&$g_LurePos[1])
					Else
						GUICtrlSetData($rodPosText,"")
					EndIf
					$g_UseLure = True
                    Else
					GUICtrlSetData($useLureText,"")
					GUICtrlSetColor($lureHeaderText, 0x808080)
					GUICtrlSetState($rodPosBtn, $GUI_DISABLE)
					GUICtrlSetState($lureBtn, $GUI_DISABLE)
					GUICtrlSetState($lureDuration, $GUI_DISABLE)
					GUICtrlSetState($lureCooldown, $GUI_DISABLE)
					GUICtrlSetData($rodPosText,"")
					GUICtrlSetData($lurePosText,"")
					$g_UseLure = False
                    EndIf
			Case $rodPosBtn
				Local $rodSet = False
				Local $dll = 'user32.dll'
				GUICtrlSetState($rodPosBtn, $GUI_DISABLE)
				GUICtrlSetState($lureBtn, $GUI_DISABLE)
				GUICtrlSetState($lureDuration, $GUI_DISABLE)
				GUICtrlSetState($lureCooldown, $GUI_DISABLE)
				While Not $rodSet
					If _IsPressed('01',$dll) Then
						; the left mouse button was pressed, set the rod position at this coordinate
						$g_RodPos = MouseGetPos()
						While _IsPressed('01',$dll)
							Sleep(5)
						WEnd
						Sleep(100)
						MouseClick("left",$g_RodPos[0],$g_RodPos[1])
						Sleep(50)
						$rodSet = True
					Else
						; no mouseclick yet
					EndIf
					Sleep(10)
				WEnd
				GUICtrlSetData($rodPosText,"Set to ("&$g_RodPos[0]&","&$g_RodPos[1]&")")
				GUICtrlSetState($rodPosBtn, $GUI_Enable)
				GUICtrlSetState($lureBtn, $GUI_Enable)
				GUICtrlSetState($lureDuration, $GUI_Enable)
				GUICtrlSetState($lureCooldown, $GUI_Enable)
			Case $lureBtn
				Local $lureSet = False
				Local $dll = 'user32.dll'
				GUICtrlSetState($rodPosBtn, $GUI_DISABLE)
				GUICtrlSetState($lureBtn, $GUI_DISABLE)
				GUICtrlSetState($lureDuration, $GUI_DISABLE)
				GUICtrlSetState($lureCooldown, $GUI_DISABLE)
				While Not $lureSet
					If _IsPressed('01',$dll) Then
						; the left mouse button was pressed, set the lure position at this coordinate
						$g_LurePos = MouseGetPos()
						While _IsPressed('01',$dll)
							Sleep(5)
						WEnd
						Sleep(100)
						MouseClick("left",$g_LurePos[0],$g_LurePos[1])
						Sleep(50)
						$lureSet = True
					Else
						; no mouseclick yet
					EndIf
					Sleep(10)
				WEnd
				GUICtrlSetData($lurePosText,"X="&$g_LurePos[0]&" Y="&$g_LurePos[1])
				GUICtrlSetState($rodPosBtn, $GUI_Enable)
				GUICtrlSetState($lureBtn, $GUI_Enable)
				GUICtrlSetState($lureDuration, $GUI_Enable)
				GUICtrlSetState($lureCooldown, $GUI_Enable)
			Case $lureDuration
      				$g_LureDuration = GUICtrlRead($lureDuration)

			Case $lureCooldown
				$g_LureCooldown = GUICtrlRead($lureCooldown)
		EndSwitch
	WEnd

	; Delete the previous GUI and all controls.
	GUIDelete($fishGui)
EndFunc

Func Terminate()
	Exit
EndFunc
