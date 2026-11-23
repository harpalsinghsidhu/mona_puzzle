[app]
icon.filename = icon.png
presplash.filename = presplash.png
presplash.color = #0A0C1C
title = Mona Puzzle
package.name = monapuzzle
package.domain = org.monapuzzle
source.dir = .
source.include_exts = py,png,jpg,kv
version = 0.1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1