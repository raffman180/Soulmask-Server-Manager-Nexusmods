Soulmask Server Manager is a lightweight, user-friendly Windows application designed to take the complexity out of hosting a dedicated server. 
Whether you are a first-time host or a seasoned admin, this tool provides a seamless interface to manage your server without touching a single command line or batch file.

## Key Features:

* One-Click Installation & Updates: Integrated SteamCMD support. Select your directory, click install, and the manager handles the rest.

* Safe Stop Technology: Never lose progress again. Our "Safe Stop" feature automatically sends a
  savecommand to the server and waits for the database to finish writing before gracefully shutting down the process via
  quit.

* Live Console Stream: Watch your server boot up and monitor logs in real-time directly within the manager's dashboard.

* Deep Auto-Detection: Lost your files? The manager can scan your drives to automatically find your
  SteamCMD.exe, WSServer-Win64-Shipping.exe, and even your world.dbsave file.

* Integrated Rules Editor: Edit your GameplaySettingsJSON files directly within the app.
  No need to hunt through folders—the manager finds and loads your latest configuration automatically.

* Network Dashboard: Quickly fetch your Public IP to share with friends and monitor your Game, Query, and Echo ports.

* Multilingual: Full support for both English and German.


## How to use:
* Setup SteamCMD: Use the "SteamCMD" button to download or link your existing SteamCMD.
* Install Server: Click "Server Install", choose your desired folder, and wait for the files to download.
* Configure: Head over to the "Settings" and "Rules" tabs to customize your server name, passwords, and gameplay mechanics.
* Launch: Go to the Dashboard and hit "Start". Your server is now running in the background!
* Stop Safely: When you're done, use the "Stop" button to ensure all world data is physically written to the world.dbbefore the process closes.

## Important Note on Connectivity
To allow friends to join your server from the internet, please ensure you have forwarded the following ports (UDP only) in your router settings to your PC's local IP:
* 8777 (Game Port)
* 27015 (Query Port)
