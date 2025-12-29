/* Minimal Windows executable that just sleeps forever
   Compile with: x86_64-w64-mingw32-gcc -o X-Plane.exe dummy_xplane.c
*/
#include <windows.h>

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrev, LPSTR lpCmdLine, int nCmdShow) {
    /* Create a named window so FindWindow can find us */
    WNDCLASSEX wc = {0};
    wc.cbSize = sizeof(WNDCLASSEX);
    wc.lpfnWndProc = DefWindowProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = "X-Plane";
    RegisterClassEx(&wc);
    
    HWND hwnd = CreateWindowEx(0, "X-Plane", "X-Plane 12", 
                                WS_OVERLAPPEDWINDOW, 
                                0, 0, 1, 1, 
                                NULL, NULL, hInstance, NULL);
    
    /* Hide the window */
    ShowWindow(hwnd, SW_HIDE);
    
    /* Message loop - run forever */
    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    
    return 0;
}
