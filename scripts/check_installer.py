with open("models/OllamaSetup.exe", "rb") as f:
    header = f.read(100000)
    if b"Inno Setup" in header:
        print("Framework: Inno Setup")
    elif b"Nullsoft" in header:
        print("Framework: NSIS")
    elif b"7z" in header:
        print("Framework: 7-Zip")
    elif b"WiX" in header or b"MSI" in header:
        print("Framework: WiX/MSI")
    else:
        print("Unknown framework. First 50 bytes:", header[:50])
