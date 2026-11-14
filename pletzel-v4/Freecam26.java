package net.pletzel.schematica;

import net.minecraft.client.Minecraft;
import net.minecraft.world.phys.Vec3;

/**
 * Render-only Freecam. Never writes player entity position, world state, server
 * packets, permissions, or camera chunk tickets. Only already received chunks
 * can be viewed. A configured vanilla KeyMapping toggles this state.
 */
public final class Freecam26 {
    private static boolean enabled;
    private static double x,y,z,oldX,oldY,oldZ;
    private static float yaw,pitch;
    private static double speed=0.55;

    private Freecam26() {}
    public static boolean active() { return enabled; }
    public static float yaw() { return yaw; }
    public static float pitch() { return pitch; }
    public static double speed() { return speed; }
    public static void speed(double blocksPerTick) {
        speed=Math.max(0.05,Math.min(4.0,blocksPerTick));
    }

    public static void toggle(Minecraft minecraft) {
        if(enabled) { disable(); return; }
        if(minecraft.level==null||minecraft.player==null||minecraft.gui.screen()!=null) return;
        x=oldX=minecraft.player.getX();
        y=oldY=minecraft.player.getEyeY();
        z=oldZ=minecraft.player.getZ();
        yaw=minecraft.player.getYRot();pitch=minecraft.player.getXRot();
        enabled=true;
        System.out.println("[PletzelFreecam] ENABLED player="+
            minecraft.player.getX()+","+minecraft.player.getY()+","+
            minecraft.player.getZ()+" rotation="+
            minecraft.player.getYRot()+","+minecraft.player.getXRot()+
            " camera="+x+","+y+","+z);
    }
    public static void disable() {
        if(enabled) {
            Minecraft mc=Minecraft.getInstance();
            System.out.println("[PletzelFreecam] DISABLED player="+
                (mc!=null&&mc.player!=null
                    ? mc.player.getX()+","+mc.player.getY()+","+mc.player.getZ()+
                      " rotation="+mc.player.getYRot()+","+mc.player.getXRot()
                    : "unavailable")+
                " priorDetachedCamera="+x+","+y+","+z);
        }
        enabled=false;
    }
    public static Vec3 position(float partialTicks) {
        float t=Math.max(0.0f,Math.min(1.0f,partialTicks));
        return new Vec3(oldX+(x-oldX)*t,oldY+(y-oldY)*t,oldZ+(z-oldZ)*t);
    }
    public static void onMouse(double dx,double dy) {
        if(!enabled)return;
        // Mouse sensitivity is already applied by the existing MouseHandler.
        yaw+=(float)(dx*0.15);
        pitch=Math.max(-90.0f,Math.min(90.0f,pitch+(float)(dy*0.15)));
    }
    public static void tick(Minecraft m) {
        if(!enabled)return;
        if(m.player==null||m.level==null||!m.player.isAlive()||m.gui.screen()!=null) {
            disable();return;
        }
        oldX=x;oldY=y;oldZ=z;
        double f=(m.options.keyUp.isDown()?1.0:0.0)-(m.options.keyDown.isDown()?1.0:0.0);
        double r=(m.options.keyRight.isDown()?1.0:0.0)-(m.options.keyLeft.isDown()?1.0:0.0);
        double u=(m.options.keyJump.isDown()?1.0:0.0)-(m.options.keyShift.isDown()?1.0:0.0);
        double norm=Math.sqrt(f*f+r*r+u*u);
        if(norm==0.0)return;
        double v=speed*(m.options.keySprint.isDown()?3.0:1.0)/norm;
        double a=Math.toRadians(yaw),b=Math.toRadians(pitch);
        // At yaw 0 the camera faces south (+Z), so screen-right is west (-X).
        x+=v*(-Math.sin(a)*Math.cos(b)*f-Math.cos(a)*r);
        y+=v*(-Math.sin(b)*f+u);
        z+=v*(Math.cos(a)*Math.cos(b)*f-Math.sin(a)*r);
    }
}
