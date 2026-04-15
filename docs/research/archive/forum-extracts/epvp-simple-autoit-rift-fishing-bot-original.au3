#include <Misc.au3>
#include <Date.au3>
#include <MsgBoxConstants.au3>
#include <WinAPI.au3>
; ********************* IMPORTANT!!!!!!!! *************************
; This is set up to work with 'autoloot' set to 'off'.
; If you use Autoloot then once you catch something it automatically
; puts the fish in your back-pack.  However, there is no simple
; event to catch that the loot box has looted and it is time to recast.
; To assure 'autoloot' is 'off' go to the following:
;
;       SYSTEM -> Settings -> Interface -> Misc
;
; setting page and uncheck the box 'Auto-Loot By Default' then
; 'Apply' that change.
;
Local $i, $j
Local $timer

Global $g_MouseX, $g_MouseY, $g_MouseCount, $g_MouseReposition
Global $g_timeLastLooted
Global $g_CsrNbr
Global $g_LastCrsNbr
Global $g_CastCount, $g_PullCount, $g_LootCount, $g_RecastCount
Global $g_XPixelOffset = 50 ; you may have to play with this value to work on resolutions other than 1920 x 1080
Global $g_YPixelOffset = 65 ; you may have to play with this value to work on resolutions other than 1920 x 1080
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
	; if the loot popup is up then this area is constant and the screen does nott change
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

Func Terminate()
	Exit
EndFunc
