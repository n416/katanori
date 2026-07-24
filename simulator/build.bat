@echo off
setlocal
rem Run from repo root (one level above this bat)
cd /d "%~dp0.."
echo =====================================================
echo  Katanori Simulator Build Script (g++ / MinGW)
echo =====================================================

where g++ >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] g++ compiler not found!
    echo Please install MinGW-w64 / w64devkit and add g++ to PATH.
    pause
    exit /b 1
)

if not exist bin mkdir bin

echo Compiling Katanori Simulator...
g++ -std=c++14 -O2 ^
    -Ifirmware/core -Ifirmware/hal ^
    firmware/core/DisplayBuffer.cpp ^
    firmware/core/StateMachine.cpp ^
    firmware/core/Face.cpp ^
    firmware/core/RobotCore.cpp ^
    simulator/win32/main_win32.cpp ^
    -lgdi32 -luser32 -lwinmm ^
    -o simulator\katanori_sim.exe

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Build succeeded: simulator\katanori_sim.exe
    echo Run "simulator\katanori_sim.exe" to launch the simulator.
) else (
    echo.
    echo [ERROR] Build failed! Check compiler error output above.
)

endlocal