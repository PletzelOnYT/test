#!/usr/bin/env python3
"""Patch active device input-mode switching into the exact pinned 26.2 source.

Run only after the existing V4 native patch stack and Singleplayer warning.
No renderer, worldgen, server, multiplayer or Schematica source is altered.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else 'engine')
teavm=root/'platform-teavm/src/main/java/net/lax1dude/eaglercraft/v1_8/internal/PlatformInput.java'
lwjgl=root/'platform-lwjgl/src/main/java/net/lax1dude/eaglercraft/v1_8/internal/PlatformInput.java'
shared=root/'platform/src/main/java/net/lax1dude/eaglercraft/v1_8/internal/PlatformInput.java'
opts=root/'game/src/main/java/net/minecraft/client/Options.java'
controls=root/'game/src/main/java/net/minecraft/client/gui/screens/options/controls/ControlsScreen.java'
language=root/'game/src/main/resources/assets/minecraft/lang/en_us.json'

def swap(src,old,new,tag):
    n=src.count(old)
    assert n==1, f'{tag}: expected exactly one source anchor; found {n}'
    return src.replace(old,new,1)

src=teavm.read_text()

src=swap(src,
    '\tprivate static boolean touchControlsEnabled = true;',
    '''\tprivate static boolean touchControlsEnabled = true;
\t// 0 = automatic last genuine device, 1 = mouse and keyboard, 2 = touchscreen.
\t// This is deliberately separate from the device's maxTouchPoints capability.
\tprivate static int inputModeOverride = 0;
\tprivate static boolean pointerEventsAvailable;
\tprivate static long lastTouchMillis = -100000L;
\tprivate static long lastGenuineMousePointerMillis = -100000L;
\tprivate static int lastTouchX = -10000, lastTouchY = -10000;
\tprivate static int lastPointerMouseX = Integer.MIN_VALUE, lastPointerMouseY = Integer.MIN_VALUE;
\tprivate static boolean touchGrabWanted;
\tprivate static EventListener<Event> inputPointerDown, inputPointerMove;
''','mode fields')

# The mouse DOM event streams are retained for actual Minecraft mouse input.
# Genuine device selection is handled by pointer events ahead of compatibility
# mouse events. A fallback exists for browsers without PointerEvent.
anchor='\t\tcanvas.addEventListener("mousedown", mousedown = new EventListener<MouseEvent>() {'
add='''\t\tpointerEventsAvailable = supportsPointerEvents();
\t\tif(pointerEventsAvailable) {
\t\t\tcanvas.addEventListener("pointerdown", inputPointerDown = new EventListener<Event>() {
\t\t\t\t@Override
\t\t\t\tpublic void handleEvent(Event evt) {
\t\t\t\t\tnotePointerEvent(evt, true);
\t\t\t\t}
\t\t\t});
\t\t\tcanvas.addEventListener("pointermove", inputPointerMove = new EventListener<Event>() {
\t\t\t\t@Override
\t\t\t\tpublic void handleEvent(Event evt) {
\t\t\t\t\tnotePointerEvent(evt, false);
\t\t\t\t}
\t\t\t});
\t\t}
'''
src=swap(src,anchor,add+anchor,'pointer device listeners')
src=swap(src,
 '''\t\t\t\thandleWindowFocus();
\t\t\t\tif(tryGrabCursorHook()) return;''',
 '''\t\t\t\tif(isTouchGeneratedMouse(evt)) return;
\t\t\t\tnoteLegacyMouse(evt, true);
\t\t\t\thandleWindowFocus();
\t\t\t\tif(tryGrabCursorHook()) return;''',
 'mouse down synthetic guard')
# mouse up might be a compatibility click too; prevent duplicate button release.
upAnchor='''\t\tcanvas.addEventListener("mouseup", mouseup = new EventListener<MouseEvent>() {
\t\t\t@Override
\t\t\tpublic void handleEvent(MouseEvent evt) {
\t\t\t\tevt.preventDefault();
\t\t\t\tevt.stopPropagation();'''
src=swap(src,upAnchor,upAnchor+'''
\t\t\t\tif(isTouchGeneratedMouse(evt)) return;
\t\t\t\tnoteLegacyMouse(evt, true);''','mouse up synthetic guard')
moveAnchor='''\t\tcanvas.addEventListener("mousemove", mousemove = new EventListener<MouseEvent>() {
\t\t\t@Override
\t\t\tpublic void handleEvent(MouseEvent evt) {
\t\t\t\tevt.preventDefault();
\t\t\t\tevt.stopPropagation();'''
src=swap(src,moveAnchor,moveAnchor+'''
\t\t\t\tif(isTouchGeneratedMouse(evt)) return;
\t\t\t\tnoteLegacyMouse(evt, false);''','mouse move synthetic guard')
src=swap(src, '\t\tisLikelyMobileBrowser = detectTouchClient();',
 '''\t\tisLikelyMobileBrowser = detectTouchClient();
\t\tlastPointerMouseX = Integer.MIN_VALUE;
\t\tlastPointerMouseY = Integer.MIN_VALUE;
\t\tlastTouchMillis = -100000L;
\t\tlastGenuineMousePointerMillis = -100000L;''','capability default')
src=swap(src,
'''\t\tisLikelyMobileBrowser = true;
\t\tList<VTouchPoint> changed = convertTouches(evt.getChangedTouches(), createIds);''',
'''\t\tisLikelyMobileBrowser = true;
\t\trememberTouch(evt);
\t\tif(isTouchClient() && touchControlsEnabled && isPointerLockedImpl()) {
\t\t\ttouchGrabWanted = true;
\t\t\tpointerLockRequested = false;
\t\t\tpointerLockWaiting = false;
\t\t\tpointerLockFlag = false;
\t\t\tunexpectedPointerLockLoss = false;
\t\t\tcallExitPointerLock(win.getDocument());
\t\t}
\t\tList<VTouchPoint> changed = convertTouches(evt.getChangedTouches(), createIds);''',
'touch activation')
src=swap(src,
'''\t\t\t\t// Android's soft keyboard must be focused in the trusted touchstart.
\t\t\t\topenTouchKeyboard();''',
'''\t\t\t\t// Android's soft keyboard must be focused in the trusted touchstart.
\t\t\t\tisLikelyMobileBrowser = true;
\t\t\t\trememberTouch(evt);
\t\t\t\topenTouchKeyboard();''','touch keyboard zone')

# In touch mode the engine must not request browser Pointer Lock. Crucially,
# the desired grab is remembered and recovered on the NEXT REAL mouse press.
old='''\t\tif(isLikelyMobileBrowser && touchControlsEnabled) {
\t\t\tpointerLockFlag = false;
\t\t\tpointerLockRequested = false;
\t\t\tpointerLockWaiting = false;
\t\t\tmouseDX = 0.0D;
\t\t\tmouseDY = 0.0D;
\t\t\treturn;
\t\t}'''
new='''\t\tif(isTouchClient() && touchControlsEnabled) {
\t\t\ttouchGrabWanted = grab;
\t\t\tpointerLockFlag = false;
\t\t\tpointerLockRequested = false;
\t\t\tpointerLockWaiting = false;
\t\t\tmouseDX = 0.0D;
\t\t\tmouseDY = 0.0D;
\t\t\tif(!grab && win != null && isPointerLockedImpl()) {
\t\t\t\tcallExitPointerLock(win.getDocument());
\t\t\t}
\t\t\treturn;
\t\t}
\t\ttouchGrabWanted = false;'''
src=swap(src,old,new,'pointer lock touch suppression')

src=swap(src,
'''\tpublic static boolean isTouchClient() {
\t\treturn isLikelyMobileBrowser;
\t}''',
'''\tpublic static boolean isTouchClient() {
\t\treturn inputModeOverride == 2 || (inputModeOverride == 0 && isLikelyMobileBrowser);
\t}

\tpublic static void setInputMode(int mode) {
\t\tinputModeOverride = mode < 0 || mode > 2 ? 0 : mode;
\t\tif(isTouchClient() && touchControlsEnabled && win != null && isPointerLockedImpl()) {
\t\t\ttouchGrabWanted = true;
\t\t\tpointerLockRequested = false;
\t\t\tpointerLockWaiting = false;
\t\t\tpointerLockFlag = false;
\t\t\tunexpectedPointerLockLoss = false;
\t\t\tcallExitPointerLock(win.getDocument());
\t\t}
\t}

\tpublic static int getInputMode() {
\t\treturn inputModeOverride;
\t}''','input mode enum API')

# The helper runs in the browser event loop: it uses genuine PointerEvent type
# (mouse/touch/pen). Compatibility mouse events never choose the device.
helpers='''\t@JSBody(params = { }, script = "return typeof window.PointerEvent === 'function';")
\tprivate static native boolean supportsPointerEvents();

\t@JSBody(params = { "evt" }, script = "return evt.pointerType === 'mouse' ? 1 : (evt.pointerType === 'touch' ? 2 : (evt.pointerType === 'pen' ? 3 : 0));")
\tprivate static native int browserPointerKind(Event evt);

\t@JSBody(params = { "evt" }, script = "return (Math.abs(evt.movementX || 0) + Math.abs(evt.movementY || 0));")
\tprivate static native double browserPointerMovement(Event evt);

\t@JSBody(params = { "evt" }, script = "return evt.clientX || 0;")
\tprivate static native int browserPointerX(Event evt);

\t@JSBody(params = { "evt" }, script = "return evt.clientY || 0;")
\tprivate static native int browserPointerY(Event evt);

\t@JSBody(params = { "evt" }, script = "return !!(evt.sourceCapabilities && evt.sourceCapabilities.firesTouchEvents);")
\tprivate static native boolean browserMouseCameFromTouch(MouseEvent evt);

\tprivate static void notePointerEvent(Event evt, boolean down) {
\t\tint kind = browserPointerKind(evt);
\t\tif(kind == 2) {
\t\t\tif(down) isLikelyMobileBrowser = true; // touch events manage actual fingers
\t\t\treturn;
\t\t}
\t\tif(kind != 1) return; // pen does not silently change either mouse/touch preference
\t\tint px = browserPointerX(evt), py = browserPointerY(evt);
\t\tboolean moved = browserPointerMovement(evt) > 1.0D;
\t\tif(lastPointerMouseX != Integer.MIN_VALUE) {
\t\t\tmoved |= Math.abs(px - lastPointerMouseX) + Math.abs(py - lastPointerMouseY) >= 3;
\t\t}
\t\tlastPointerMouseX = px;
\t\tlastPointerMouseY = py;
\t\tif(!down && !moved) return;
\t\tlastGenuineMousePointerMillis = PlatformRuntime.steadyTimeMillis();
\t\tisLikelyMobileBrowser = false;
\t\tif(down && !isTouchClient() && touchGrabWanted && !remoteDesktopMouseMode) {
\t\t\t// Trusted pointerdown has user activation; delayed game ticks don't.
\t\t\tmouseSetGrabbed(true);
\t\t}
\t}

\tprivate static void rememberTouch(TouchEvent evt) {
\t\tlastTouchMillis = PlatformRuntime.steadyTimeMillis();
\t\tif(evt.getChangedTouches().getLength() > 0) {
\t\t\tTouch first = evt.getChangedTouches().get(0);
\t\t\tlastTouchX = (int)getCanvasTouchX(first, canvas);
\t\t\tlastTouchY = (int)getCanvasTouchY(first, canvas);
\t\t}
\t}

\tprivate static boolean isTouchGeneratedMouse(MouseEvent evt) {
\t\tif(browserMouseCameFromTouch(evt)) return true;
\t\tlong age = PlatformRuntime.steadyTimeMillis() - lastTouchMillis;
\t\tif(age < 0L || age > 700L) return false;
\t\tif(lastGenuineMousePointerMillis >= lastTouchMillis) return false;
\t\t// Older browsers missing sourceCapabilities may produce click/mousemove
\t\t// compatibility events at the last touch position. Only quarantine that
\t\t// small area for a short time; genuine PointerEvent mouse always wins.
\t\tint x = (int)getCanvasMouseX(evt, canvas, Math.max(1, canvas.getWidth()));
\t\tint y = (int)getCanvasMouseY(evt, canvas, Math.max(1, canvas.getHeight()));
\t\treturn Math.abs(x - lastTouchX) <= 32 && Math.abs(y - lastTouchY) <= 32;
\t}

\tprivate static void noteLegacyMouse(MouseEvent evt, boolean click) {
\t\tif(pointerEventsAvailable) return;
\t\tif(click || Math.abs(evt.getMovementX()) + Math.abs(evt.getMovementY()) >= 2) {
\t\t\tisLikelyMobileBrowser = false;
\t\t}
\t}

'''
src=swap(src,
 '\tpublic static boolean isTouchClient() {',
 helpers+'\tpublic static boolean isTouchClient() {','genuine pointer helper')

# Tear down listeners cleanly; no leaks after a game restart.
teardown='''\t\tif(inputPointerDown != null) {
\t\t\tcanvas.removeEventListener("pointerdown", inputPointerDown);
\t\t\tinputPointerDown = null;
\t\t}
\t\tif(inputPointerMove != null) {
\t\t\tcanvas.removeEventListener("pointermove", inputPointerMove);
\t\t\tinputPointerMove = null;
\t\t}
'''
src=swap(src,
'\t\tif(mousedown != null) {\n\t\t\tcanvas.removeEventListener("mousedown", mousedown);',
teardown+'\t\tif(mousedown != null) {\n\t\t\tcanvas.removeEventListener("mousedown", mousedown);','cleanup pointer listeners')
teavm.write_text(src)

src=shared.read_text()
src=swap(src,
'\tpublic static native boolean isTouchClient();',
'\tpublic static native boolean isTouchClient();\n\n\tpublic static native void setInputMode(int mode);\n\n\tpublic static native int getInputMode();','shared API')
shared.write_text(src)

src=lwjgl.read_text()
src=swap(src,
'\tpublic static boolean isTouchClient() {\n\t\treturn false;\n\t}',
'''\tpublic static boolean isTouchClient() {
\t\treturn false;
\t}

\tpublic static void setInputMode(int mode) {
\t\t// Desktop GLFW controls stay mouse-driven.
\t}

\tpublic static int getInputMode() {
\t\treturn 1;
\t}''','desktop stubs')
lwjgl.write_text(src)

src=opts.read_text()
target='''   private static final Component TOUCH_CONTROLS_TOOLTIP = Component.translatable("options.eaglerTouchControls.tooltip");'''
added='''   private static final Component INPUT_MODE_TOOLTIP = Component.translatable("options.pletzelInputMode.tooltip");
   private final OptionInstance<Integer> pletzelInputMode = new OptionInstance<>(
      "options.pletzelInputMode", OptionInstance.cachedConstantTooltip(INPUT_MODE_TOOLTIP),
      (caption, value) -> Component.translatable("options.pletzelInputMode." + value),
      new OptionInstance.Enum<>(java.util.List.of(0, 1, 2), com.mojang.serialization.Codec.intRange(0, 3)),
      0, net.lax1dude.eaglercraft.v1_8.internal.PlatformInput::setInputMode
   );
'''
src=swap(src,target,added+target,'options mode field')
src=swap(src,
'''   public OptionInstance<Boolean> touchControls() {
      return this.touchControls;
   }''',
'''   public OptionInstance<Boolean> touchControls() {
      return this.touchControls;
   }

   public OptionInstance<Integer> pletzelInputMode() {
      return this.pletzelInputMode;
   }''','options getter')
src=swap(src,
'      access.process("eaglerTouchControls", this.touchControls);',
'      access.process("eaglerTouchControls", this.touchControls);\n      access.process("pletzelInputMode", this.pletzelInputMode);','settings persistence')
src=swap(src,
'''         net.lax1dude.eaglercraft.v1_8.internal.PlatformInput.setTouchControlsEnabled(this.touchControls.get());''',
'''         net.lax1dude.eaglercraft.v1_8.internal.PlatformInput.setTouchControlsEnabled(this.touchControls.get());
         net.lax1dude.eaglercraft.v1_8.internal.PlatformInput.setInputMode(this.pletzelInputMode.get());''','settings on load')
opts.write_text(src)

src=controls.read_text()
# Keep the old Touch Controls checkbox and RDP setting accessible. Both
# touchscreen and desktop layouts now expose Input Mode in vanilla Controls.
src=swap(src,
'''            options.touchControls(),
            options.rdpMouseMode(),''',
'''            options.pletzelInputMode(),
            options.touchControls(),
            options.rdpMouseMode(),''','touch control options')
src=swap(src,
'''         options.toggleUse(),
         options.rdpMouseMode(),''',
'''         options.toggleUse(),
         options.pletzelInputMode(),
         options.touchControls(),
         options.rdpMouseMode(),''','desktop control options')
controls.write_text(src)

src=language.read_text()
key='  "options.eaglerTouchControls": "Touch Controls",'
addition='''  "options.pletzelInputMode": "Input Mode",
  "options.pletzelInputMode.tooltip": "Auto follows your last genuine touch or physical mouse input. Mouse and Keyboard forces desktop controls; Touchscreen forces touch controls.",
  "options.pletzelInputMode.0": "Auto",
  "options.pletzelInputMode.1": "Mouse & Keyboard",
  "options.pletzelInputMode.2": "Touchscreen",
'''
src=swap(src,key,addition+key,'English controls translation')
language.write_text(src)

assert 'PletzelSingleplayerWarningScreen.java' in {x.name for x in (root/'game/src/main/java/net/minecraft/client/gui/screens').iterdir()},'Native warning missing!'
print('PASS: active native touch/mouse mode; pointer-kind classifier; synthetic mouse suppression')
print('PASS: platform APIs (browser, shared, desktop); persisted Auto/Mouse/Touch cycle in Controls')
print('PASS: preserved Singleplayer warning, remote mouse and touch toolbar setting')
