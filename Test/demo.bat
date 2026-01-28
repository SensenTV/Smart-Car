@echo off
chcp 65001 >nul
title Smart-Car Demo Controller

:menu
cls
echo ==================================================
echo    SMART-CAR DEMO CONTROLLER
echo ==================================================
echo    Fahrzeug: TEST001
echo ==================================================
echo.
echo [EINZELNE EREIGNISSE]
echo   1 - Fehler P0300 (Motor) ausloesen
echo   2 - Fehler P0420 (Katalysator) ausloesen
echo   3 - Fehler beheben (P0300)
echo   4 - Alarm: Kraftstoff niedrig
echo   5 - Alarm: Batterie kritisch
echo   6 - Alarm: Geschwindigkeit zu hoch
echo   7 - Fahrt beenden (Trip)
echo   8 - Status: Fahrzeug faehrt
echo   9 - Status: Fahrzeug parkt
echo.
echo [SZENARIEN]
echo   A - Notfall (mehrere Alarme)
echo   B - Normaler Tag (komplette Fahrt)
echo.
echo   0 - Beenden
echo ==================================================
echo.

set /p choice="Auswahl: "

if "%choice%"=="0" goto end
if "%choice%"=="1" goto error_p0300
if "%choice%"=="2" goto error_p0420
if "%choice%"=="3" goto error_fix
if "%choice%"=="4" goto alert_fuel
if "%choice%"=="5" goto alert_battery
if "%choice%"=="6" goto alert_speed
if "%choice%"=="7" goto trip
if "%choice%"=="8" goto state_driving
if "%choice%"=="9" goto state_parked
if /i "%choice%"=="A" goto scenario_emergency
if /i "%choice%"=="B" goto scenario_day
goto menu

:error_p0300
echo [SENDE] Fehler P0300 (Motor)...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "error,TEST001,P0300,1"
echo [OK] Gesendet!
pause
goto menu

:error_p0420
echo [SENDE] Fehler P0420 (Katalysator)...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "error,TEST001,P0420,1"
echo [OK] Gesendet!
pause
goto menu

:error_fix
echo [SENDE] Fehler P0300 behoben...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "error,TEST001,P0300,0"
echo [OK] Gesendet!
pause
goto menu

:alert_fuel
echo [SENDE] Alarm: Kraftstoff niedrig...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "alert,TEST001,fuel_low,Kraftstoff_unter_10L"
echo [OK] Gesendet!
pause
goto menu

:alert_battery
echo [SENDE] Alarm: Batterie kritisch...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "alert,TEST001,battery_low,Batterie_unter_11V"
echo [OK] Gesendet!
pause
goto menu

:alert_speed
echo [SENDE] Alarm: Geschwindigkeit zu hoch...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "alert,TEST001,overspeed,Geschwindigkeit_ueber_130kmh"
echo [OK] Gesendet!
pause
goto menu

:trip
echo [SENDE] Fahrt beendet...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "trip,TEST001,TRIP_DEMO,2400,6.5,4.2,5.1"
echo [OK] Gesendet!
pause
goto menu

:state_driving
echo [SENDE] Status: Fahrzeug faehrt...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "state,TEST001,driving,42.5,12.6"
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "gps,TEST001,53.5511,9.9937,65"
echo [OK] Gesendet!
pause
goto menu

:state_parked
echo [SENDE] Status: Fahrzeug parkt...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "state,TEST001,parked,40.0,12.8"
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "gps,TEST001,53.5520,10.0050,0"
echo [OK] Gesendet!
pause
goto menu

:scenario_emergency
echo.
echo [SZENARIO] Notfall-Simulation...
echo.
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "state,TEST001,driving,8.5,11.2"
timeout /t 1 >nul
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "error,TEST001,P0300,1"
timeout /t 1 >nul
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "alert,TEST001,fuel_low,KRITISCH_nur_noch_5L"
timeout /t 1 >nul
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "alert,TEST001,battery_low,Batterie_kritisch"
timeout /t 1 >nul
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "error,TEST001,C0035,1"
echo.
echo [OK] Notfall-Szenario abgeschlossen!
pause
goto menu

:scenario_day
echo.
echo [SZENARIO] Normaler Arbeitstag...
echo.
echo - Fahrzeug startet...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "state,TEST001,idle,48.0,12.9"
timeout /t 2 >nul
echo - Fahrt beginnt...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "state,TEST001,driving,47.5,12.7"
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "gps,TEST001,53.55,10.0,40"
timeout /t 2 >nul
echo - Unterwegs...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "state,TEST001,driving,45.0,12.5"
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "gps,TEST001,53.56,10.02,80"
timeout /t 2 >nul
echo - Fahrzeug parkt...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "state,TEST001,parked,43.0,12.8"
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "gps,TEST001,53.57,10.05,0"
timeout /t 1 >nul
echo - Fahrt abgeschlossen...
docker exec mosquitto mosquitto_pub -t "smartcar/TEST001" -m "trip,TEST001,TRIP_TAG,3600,5.0,3.5,4.2"
echo.
echo [OK] Arbeitstag abgeschlossen!
pause
goto menu

:end
echo Auf Wiedersehen!
