#!/usr/bin/env python3
"""Fail-closed checks for native independent buttons and ordinary-map previews."""
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
game=root/"game/src/main/java"
teavm=root/"platform-teavm/src/main/java"
def read(relative,base=game):
    return (base/relative).read_text()
screen=read("net/pletzel/schematica/SchematicaScreen.java")
assert screen.count('toggle(left,y,"Easy Pick"')==1
assert screen.count('toggle(right,y,"Easy Place"')==1
assert "PITCH=28" in screen
assert "this.rebuildWidgets()" in screen
assert "Prev Page" in screen and "Next Page" in screen
assert "Layer Controls" in screen
assert "Position / Transform" in screen
assert "EagRuntime.displayFileChooser(\"\",null)" in screen
assert "SchematicaSession.loadAny(" in screen
assert "PletzelSchematicImport] LOADED" in screen
opts=read("net/minecraft/client/Options.java")
assert 'access.process("pletzelEasyPick", this.pletzelEasyPick)' in opts
assert 'access.process("pletzelEasyPlace", this.pletzelEasyPlace)' in opts
assert 'OptionInstance.createBoolean("pletzelEasyPick", false)' in opts
assert 'OptionInstance.createBoolean("pletzelEasyPlace", false)' in opts
store=read("net/pletzel/maptooltip/MapArtStore26.java")
assert "policy(id)!=EXCLUDED" in store
assert "getPletzelActiveWorldId()" in store
assert "mc.isLocalServer()" in store
worker=read("net/lax1dude/eaglercraft/v1_8/sp/SingleplayerServerController26.java")
assert "pletzelActiveWorldId=worldName" in worker
assert "getPletzelActiveWorldId()" in worker
assert "policy(id)==ART" not in store
assert "MapTooltipData.isExplorer(stack)" in store
assert "hasObservedColors" in store
client=read("net/pletzel/maptooltip/MapTooltipClientComponent.java")
assert "Waiting for map pixels" in client
assert "MapArtStore26.cachedData(id)" in client
assert "graphics.map(state)" in client
data=read("net/pletzel/maptooltip/MapTooltipData.java")
assert "MapDecorationTypes.WOODLAND_MANSION" in data
assert "MapDecorationTypes.OCEAN_MONUMENT" in data
assert "MapDecorationTypes.RED_X" in data
app=read("net/lax1dude/eaglercraft/v1_8/internal/PlatformApplication.java",teavm)
bridge=read("net/lax1dude/eaglercraft/v1_8/internal/PletzelMapArtIndexedDB26.java",teavm)
assert "PletzelMapArtIndexedDB26.put(eagName,b64)" in app
assert "PletzelMapArtIndexedDB26.get(eagName)" in app
assert "indexedDB.open('pletzel-map-art-v1',1)" in bridge
assert "createObjectStore('pixels')" in bridge
assert "transaction('pixels','readwrite')" in bridge
assert "transaction('pixels','readonly')" in bridge
print("RESTORED_SCHEMATICA_AND_INDEXEDDB_SOURCE_CONTRACT_PASS")
print("NOTE: source contracts are not gameplay acceptance or persisted-browser proof")
