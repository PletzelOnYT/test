#!/usr/bin/env python3
"""Restore independent Easy Pick/Easy Place GUI and IndexedDB-backed map cache.

Runs LAST, after native 26.2 Schematica + four-format + Easy Pick + Easy Place
patches. All replacements fail closed on a shifted upstream source signature.
"""
from pathlib import Path
import shutil,sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "engine")
game=root/"game/src/main/java"
teavm=root/"platform-teavm/src/main/java"
here=Path(__file__).parent

def one(path,old,new):
    text=path.read_text()
    count=text.count(old)
    assert count==1,(str(path),count,old[:90])
    path.write_text(text.replace(old,new,1))
    print("PLETZEL_MENU_MAP_FIXED",str(path))

screen=game/"net/pletzel/schematica/SchematicaScreen.java"
previous=screen.read_text()
# The previous Easy Place patch removed the separate Easy Pick button.
assert previous.count('"Building / Easy Place"')==1
assert "EagRuntime.displayFileChooser" in previous
assert "SchematicaSession.loadAny(" in previous
source=(here/"SchematicaScreenRestored26.java").read_text()
assert "toggle(left,y,\"Easy Pick\"" in source
assert "toggle(right,y,\"Easy Place\"" in source
assert "PITCH=28" in source
assert "List<IntConsumer> rows" in source
assert "SchematicaSession.loadAny(" in source
screen.write_text(source)

# Critical WasmGC cache identity fix: dedicated-server worlds never put an
# IntegratedServer in Minecraft.singleplayerServer on the browser client.
# Bind the exact saved-world ID to the client-side controller that launches the
# worker, so two distinct local worlds cannot share map IDs accidentally.
controller=game/"net/lax1dude/eaglercraft/v1_8/sp/SingleplayerServerController26.java"
one(controller,
'''\tprivate static volatile int state = STATE_NONE;''',
'''\tprivate static volatile int state = STATE_NONE;
    private static volatile String pletzelActiveWorldId;''')
one(controller,
'''\tpublic static int getState() {''',
'''    public static String getPletzelActiveWorldId() {
        return pletzelActiveWorldId;
    }

\tpublic static int getState() {''')
one(controller,
'''\tprivate static void beginLocalServerLaunch(String worldName) {''',
'''\tprivate static void beginLocalServerLaunch(String worldName) {
        // Keep the authoritative LevelStorageAccess.getLevelId(), not a
        // world display name or guessed Minecraft server address.
        pletzelActiveWorldId=worldName;''')
one(controller,
'''\t\tstate = STATE_NONE;
\t\tworkerBooted = false;''',
'''\t\tstate = STATE_NONE;
        pletzelActiveWorldId=null;
\t\tworkerBooted = false;''')

# Native browser IndexedDB, returning a synchronous cache value only after
# its asynchronous disk get succeeds. Never block WebGL frames or game ticks.
bridge=teavm/"net/lax1dude/eaglercraft/v1_8/internal/PletzelMapArtIndexedDB26.java"
assert not bridge.exists(),"Duplicate IndexedDB bridge"
bridge.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(here/"PletzelMapArtIndexedDB26.java",bridge)

app=teavm/"net/lax1dude/eaglercraft/v1_8/internal/PlatformApplication.java"
one(app,
'''\t\tString b64 = data != null ? Base64.getEncoder().encodeToString(data) : null;
\t\ttry {
\t\t\tStorage s = Window.current().getLocalStorage();''',
'''\t\tString b64 = data != null ? Base64.getEncoder().encodeToString(data) : null;
        if (name.startsWith("pletzel.mapart26.pixel.")
                && PletzelMapArtIndexedDB26.put(eagName,b64)) {
            // 16,384 real map-color bytes belong in IndexedDB, not the
            // browser's small localStorage options quota.
            try {
                Storage prior=Window.current().getLocalStorage();
                if(prior!=null)prior.removeItem(eagName);
            } catch(Throwable ignored) {}
            if(hooks)adapter.getHooks().callLocalStorageSavedHook(name,b64);
            return;
        }
\t\ttry {
\t\t\tStorage s = Window.current().getLocalStorage();''')
one(app,
'''\t\tString eagName = adapter.getLocalStorageNamespace() + "." + name;
\t\tbyte[] hooked = null;''',
'''\t\tString eagName = adapter.getLocalStorageNamespace() + "." + name;
        if(name.startsWith("pletzel.mapart26.pixel.")) {
            // Nonblocking cached read. A pending IndexedDB get returns null;
            // the unchanged tooltip keeps its reserved box until hydrated.
            String saved=PletzelMapArtIndexedDB26.get(eagName);
            if(saved!=null) {
                try { return Base64.getMimeDecoder().decode(saved); }
                catch(Throwable ignored) {}
            }
        }
\t\tbyte[] hooked = null;''')
one(app,
'''\t\t\t\t\tif(str != null) {
\t\t\t\t\t\treturn Base64.getMimeDecoder().decode(str);''',
'''\t\t\t\t\tif(str != null) {
                        // Migrate previously learned map pixels from older
                        // localStorage builds into the new durable IndexedDB.
                        if(name.startsWith("pletzel.mapart26.pixel."))
                            PletzelMapArtIndexedDB26.put(eagName,str);
\t\t\t\t\t\treturn Base64.getMimeDecoder().decode(str);''')
print("PLETZEL_GUI_INDEPENDENT_EASYPICK_EASYPLACE_AND_INDEXEDDB_READY")
