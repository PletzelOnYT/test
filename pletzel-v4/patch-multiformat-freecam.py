#!/usr/bin/env python3
"""Apply 26.2 no-voice Litematica multi-format and Freecam edits after native GUI/renderer fixes.
Fail closed on changed source signatures, never silently skip a requested integration."""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path("engine")
base=root/"game/src/main/java"
def edit(rel,transform):
    p=base/rel
    before=p.read_text()
    after=transform(before)
    if before==after: raise RuntimeError("No changes in "+str(p))
    p.write_text(after)
    print("PATCHED",p,len(before),"->",len(after))

def rep(s,old,new):
    n=s.count(old)
    if n!=1:raise RuntimeError("Expected exactly one "+repr(old[:100])+", found "+str(n))
    return s.replace(old,new,1)

def method(s, signature, new):
    at=s.find(signature)
    if at<0:raise RuntimeError("Method signature missing: "+signature)
    brace=s.find("{",at)
    if brace<0:raise RuntimeError("Missing method body: "+signature)
    depth=0
    for i in range(brace,len(s)):
        if s[i]=="{":depth+=1
        elif s[i]=="}":
            depth-=1
            if depth==0:return s[:at]+new+s[i+1:]
    raise RuntimeError("Unbalanced method "+signature)

def session(s):
    s=rep(s,"private static final int MAX_BLOCKS = 4096; // Explicit preview-size limit; refuse, never silently truncate.","// No fixed schematic block-count ceiling; actual Java indexed-volume capacity applies.")
    # Decode through the new four-format reader; preserve existing session/renderer APIs.
    new=String=None
    new='''public static void loadClassic(final byte[] bytes) throws IOException {
        loadAny(bytes, ".schematic");
    }

    public static void loadAny(final byte[] bytes, final String filename) throws IOException {
        SchematicFormats26.Parsed parsed=SchematicFormats26.read(bytes,filename);
        // Publish only after successful complete parse; corrupted input preserves old schematic.
        cells=Collections.unmodifiableList(parsed.cells());
        width=parsed.width(); height=parsed.height(); length=parsed.length();
        unknownCount=parsed.unknownCount();
        origin=BlockPos.ZERO; rotation=0; flipX=false; flipZ=false; layer=0; layerMode=0;
        visible=true; version++;
        SchematicaWorldRenderer.clearModelCache();
    }'''
    s=method(s,"public static void loadClassic(final byte[] bytes) throws IOException",new)
    return s

def screen(s):
    s=s.replace("Choose a classic .schematic file","Choose .litematic / .schematic / .schem / .nbt")
    s=rep(s,
       'EagRuntime.displayFileChooser("application/octet-stream", ".schematic");',
       'EagRuntime.displayFileChooser("application/octet-stream", ".litematic,.schematic,.schem,.nbt");')
    s=s.replace("Choose .schematic in the browser file picker","Choose a supported schematic in the browser file picker")
    s=rep(s,
       'if (!result.fileName.toLowerCase(java.util.Locale.ROOT).endsWith(".schematic")) {\n                status="Only classic .schematic supported"; return;\n            }',
       'if (result.fileName==null || !result.fileName.toLowerCase(java.util.Locale.ROOT).matches(".*\\\\.(litematic|schematic|schem|nbt)$")) {\n                status="Supported: .litematic, .schematic, .schem, .nbt"; return;\n            }')
    s=rep(s,"SchematicaSession.loadClassic(result.fileName, result.fileData);",
         "SchematicaSession.loadAny(result.fileData, result.fileName);")
    # Keep this slider inside the existing Schematica screen.
    s=rep(s,'add(right,y,"Done",this::onClose);',
       '''this.addRenderableWidget(new AbstractSliderButton(right,y,150,20,
            Component.literal("Freecam Speed"),Math.max(0.0,Math.min(1.0,(Freecam26.speed()-0.05)/3.95))) {
            @Override protected void updateMessage() {
                setMessage(Component.literal("Freecam Speed: "+String.format(java.util.Locale.ROOT,"%.2f",Freecam26.speed())));
            }
            @Override protected void applyValue() { Freecam26.speed(0.05+this.value*3.95); }
        });
        y+=24;
        add(right,y,"Done",this::onClose);''')
    return s

def renderer(s):
    # This work is incremental; never iterate a million cells in one render frame.
    s=rep(s,"private static long sectionCacheVersion=Long.MIN_VALUE;",
          "private static long sectionCacheVersion=Long.MIN_VALUE;\n    private static int sectionBuildCursor;")
    key="if (sectionCacheVersion != SchematicaSession.version()) {"
    s=rep(s,key,"if (sectionCacheVersion != SchematicaSession.version() || sectionBuildCursor < SchematicaSession.cells().size()) {")
    start=s.find("private static void rebuildSections(")
    if start<0: raise RuntimeError("Missing renderer section builder")
    brace=s.find("{",start)
    depth=0
    for i in range(brace,len(s)):
        if s[i]=="{":depth+=1
        elif s[i]=="}":
            depth-=1
            if depth==0:break
    old=s[brace+1:i]
    if "SECTION_CACHE.clear();" not in old or "for (SchematicaSession.Cell c : SchematicaSession.cells())" not in old:
        raise RuntimeError("Unexpected section builder body: "+old[:600])
    changed=old.replace("SECTION_CACHE.clear();",
       """if (sectionCacheVersion != SchematicaSession.version()) {
            SECTION_CACHE.clear();
            sectionBuildCursor=0;
        }""",1)
    changed=changed.replace("for (SchematicaSession.Cell c : SchematicaSession.cells()) {",
       """final java.util.List<SchematicaSession.Cell> source=SchematicaSession.cells();
        final int end=(int)Math.min((long)source.size(),(long)sectionBuildCursor+2048L);
        for (int index=sectionBuildCursor; index<end; index++) {
            SchematicaSession.Cell c=source.get(index);""",1)
    marker="sectionCacheVersion=SchematicaSession.version();"
    if marker not in changed:raise RuntimeError("Renderer did not publish section cache version")
    changed=changed.replace(marker,"sectionBuildCursor=end;\n        "+marker,1)
    s=s[:brace+1]+changed+s[i:]
    s=rep(s,"SECTION_CACHE.clear();\n        sectionCacheVersion=Long.MIN_VALUE;",
      "SECTION_CACHE.clear();\n        sectionBuildCursor=0;\n        sectionCacheVersion=Long.MIN_VALUE;")
    return s

def options(s):
    s=rep(s,
       'public final KeyMapping keyUp = new KeyMapping("key.forward", 87, KeyMapping.Category.MOVEMENT);',
       'public final KeyMapping keyFreecam = new KeyMapping("Freecam - Toggle Freecam", -1, KeyMapping.Category.MISC);\n   public final KeyMapping keyUp = new KeyMapping("key.forward", 87, KeyMapping.Category.MOVEMENT);')
    s=rep(s,"            this.keyUp,\n            this.keyLeft,",
       "            this.keyFreecam,\n            this.keyUp,\n            this.keyLeft,")
    return s

def camera(s):
    needle="private void alignWithEntity(final float partialTicks) {"
    return rep(s,needle,needle+'''
      if (net.pletzel.schematica.Freecam26.active()) {
         this.setRotation(net.pletzel.schematica.Freecam26.yaw(),net.pletzel.schematica.Freecam26.pitch());
         this.setPosition(net.pletzel.schematica.Freecam26.position(partialTicks));
         this.detached=true;
         return;
      }''')

def minecraft(s):
    s=rep(s,"public void tick() {\n      boolean eaglerPerfEnabled",
       "public void tick() {\n      net.pletzel.schematica.Freecam26.tick(this);\n      boolean eaglerPerfEnabled")
    s=rep(s,"private void handleKeybinds() {",
       """private void handleKeybinds() {
      while (this.options.keyFreecam.consumeClick()) net.pletzel.schematica.Freecam26.toggle(this);
      if (net.pletzel.schematica.Freecam26.active()) return;""")
    s=rep(s,"public void setLevel(final ClientLevel level) {",
       "public void setLevel(final ClientLevel level) {\n      net.pletzel.schematica.Freecam26.disable();")
    s=rep(s,"private boolean startAttack() {",
       "private boolean startAttack() {\n      if (net.pletzel.schematica.Freecam26.active()) return false;")
    s=rep(s,"private void startUseItem() {",
       "private void startUseItem() {\n      if (net.pletzel.schematica.Freecam26.active()) return;")
    s=rep(s,"private void continueAttack(final boolean down) {",
       "private void continueAttack(final boolean down) {\n      if (net.pletzel.schematica.Freecam26.active()) return;")
    return s

def keyboard(s):
    return rep(s,"public void tick() {",
       """public void tick() {
      if (net.pletzel.schematica.Freecam26.active()) {
         this.keyPresses=Input.EMPTY;
         this.moveVector=Vec2.ZERO;
         return;
      }""")

def mouse(s):
    old='''this.minecraft.player.turn(this.minecraft.options.invertMouseX().get() ? -xo : xo, this.minecraft.options.invertMouseY().get() ? -yo : yo);'''
    new='''double turnX=this.minecraft.options.invertMouseX().get() ? -xo : xo;
         double turnY=this.minecraft.options.invertMouseY().get() ? -yo : yo;
         if (net.pletzel.schematica.Freecam26.active())
            net.pletzel.schematica.Freecam26.onMouse(turnX, turnY);
         else this.minecraft.player.turn(turnX, turnY);'''
    return rep(s,old,new)

import shutil
target=base/"net/pletzel/schematica"
target.mkdir(parents=True,exist_ok=True)
for filename in ("SchematicFormats26.java","Freecam26.java"):
    shutil.copyfile(Path(__file__).with_name(filename),target/filename)
edit("net/pletzel/schematica/SchematicaSession.java",session)
edit("net/pletzel/schematica/SchematicaScreen.java",screen)
edit("net/pletzel/schematica/SchematicaWorldRenderer.java",renderer)
edit("net/minecraft/client/Options.java",options)
edit("net/minecraft/client/Camera.java",camera)
edit("net/minecraft/client/Minecraft.java",minecraft)
edit("net/minecraft/client/player/KeyboardInput.java",keyboard)
edit("net/minecraft/client/MouseHandler.java",mouse)
print("NATIVE_MULTIFORMAT_FREECAM_PATCH_APPLIED")
