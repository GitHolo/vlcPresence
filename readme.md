# vlc discord rich presence

this is a script that bridges vlc media player and discord. it pulls what you're currently watching or listening to through vlc's local web interface, strips out the junk from standard release filenames to find the actual title, grabs cover art from imdb or itunes, and pushes it to your discord profile.... if you want that... ykno nobody will care anyway right?

### setup

**1. configure vlc**
open vlc and go to tools -> preferences
at the bottom left under "show settings", click "all"
go to interface -> main interfaces and check the "web" box
drop down the "main interfaces" menu on the left and click "lua"
under "lua http", type in a password
save your settings and restart vlc

**2. dependencies**
you need python. obviously.
open your terminal in the folder and run:

```sh
pip install pypresence requests
```

**3. passwords and config**
the script looks for your vlc password in your environment variables.
you can either set `VLC_PASSWORD` on your os, or just open `vlc.pyw` and hardcode the password you just made into the config section.
if you hardcode it, just don't push it back to github. 

**4. running it**
if you want to test it with a terminal open, run `python vlc.py`

if you want it to run silently in the background so you don't have to look at it or keep your editor open, use the `.pyw` version. it hides the window.
just double click `vlc.pyw` to start it.
put a shortcut to it in `shell:startup` on windows if you want it to run on boot and just forget it exists.
on linux, you can write a quick systemd user service for it so it runs headless.