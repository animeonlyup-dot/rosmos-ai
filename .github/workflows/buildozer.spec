[app]
title = RosMos AI
package.name = rosmos
package.domain = org.rosmos

source.dir = .
source.include_exts = py,jpg,png

version = 1.0

requirements = python3,kivy,kivymd,requests,pyttsx3,speechrecognition,plyer

orientation = portrait

android.permissions = INTERNET,RECORD_AUDIO

[buildozer]
log_level = 2
warn_on_root = 1
