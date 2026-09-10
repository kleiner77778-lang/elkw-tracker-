[app]

title = Atlas E-Lkw Tracker
package.name = elkwtracker
package.domain = org.elkw
source.include_exts = py,png,jpg,kv,atlas,json
source.dir = .
version = 0.1
requirements = python3,kivy,requests,urllib3,certifi,idna,charset-normalizer
orientation = portrait
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,FOREGROUND_SERVICE
android.api = 33
android.accept_sdk_license = True
android.minapi = 21
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
