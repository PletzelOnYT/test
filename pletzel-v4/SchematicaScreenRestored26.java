package net.pletzel.schematica;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntConsumer;
import net.lax1dude.eaglercraft.v1_8.EagRuntime;
import net.lax1dude.eaglercraft.v1_8.internal.FileChooserResult;
import net.minecraft.client.OptionInstance;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.AbstractSliderButton;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/**
 * Responsive Minecraft-native Schematica controls.
 * The primary panel ALWAYS exposes Easy Pick and Easy Place separately.
 * Other controls are organized into Position, Layers, and Advanced panels.
 * Pages are accessible from the footer when the GUI is too small to fit all
 * buttons with a minimum eight logical pixels of vertical separation.
 */
public final class SchematicaScreen extends Screen {
    private static final int TOP=56, PITCH=28, BUTTON_H=20, GAP=8;
    private final Screen parent;
    private boolean choosing;
    private String status="Load .litematic / .schematic / .schem / .nbt";
    private int panel=0, page=0, buttonWidth=150;

    public SchematicaScreen(Screen parent) {
        super(Component.literal("Schematica"));
        this.parent=parent;
    }

    private void add(int x,int y,String label,Runnable action) {
        this.addRenderableWidget(Button.builder(Component.literal(label),b->action.run())
            .bounds(x,y,buttonWidth,BUTTON_H).build());
    }
    private void toggle(int x,int y,String label,OptionInstance<Boolean> setting) {
        this.addRenderableWidget(Button.builder(
            Component.literal(label+": "+(setting.get()?"ON":"OFF")),
            b->{
                boolean next=!setting.get();
                setting.set(next);
                this.minecraft.options.save();
                System.out.println("[PletzelBuildSettings] "+label+"="+next);
                if(label.equals("Easy Pick"))
                    System.out.println("[PletzelEasyPick] SETTING enabled="+next);
                status=label+" "+(next?"enabled":"disabled")+" (saved)";
                this.rebuildWidgets();
            }).bounds(x,y,buttonWidth,BUTTON_H).build());
    }
    private void selectPanel(int next) {
        panel=next;page=0;this.rebuildWidgets();
    }
    private void loadFile() {
        choosing=true;
        EagRuntime.clearFileChooserResult();
        // Deliberately no restrictive MIME filter: macOS may not recognize
        // .schem and .litematic as application/octet-stream.
        EagRuntime.displayFileChooser("",null);
        status="Choose .litematic / .schematic / .schem / .nbt";
    }

    @Override protected void init() {
        System.out.println("[PletzelSchematicaScreen] OPEN");
        buttonWidth=Math.min(150,Math.max(66,(this.width-28)/2));
        final int left=this.width/2-buttonWidth-GAP/2;
        final int right=this.width/2+GAP/2;
        final List<IntConsumer> rows=new ArrayList<>();

        if(panel==0) {
            rows.add(y->{
                add(left,y,"Load Schematic",this::loadFile);
                add(right,y,"Unload Schematic",()->{
                    SchematicaSession.unload();status="Schematic unloaded";
                });
            });
            rows.add(y->{
                add(left,y,"Show / Hide",()->
                    SchematicaSession.setVisible(!SchematicaSession.visible()));
                this.addRenderableWidget(new AbstractSliderButton(right,y,buttonWidth,BUTTON_H,
                    Component.literal("Opacity"),SchematicaSession.opacity()) {
                    @Override protected void updateMessage() {
                        setMessage(Component.literal("Opacity: "+Math.round(
                            SchematicaSession.opacity()*100)+"%"));
                    }
                    @Override protected void applyValue() {
                        SchematicaSession.setOpacity((float)this.value);
                    }
                });
            });
            // The TWO INDEPENDENT settings are never hidden under Building.
            rows.add(y->{
                toggle(left,y,"Easy Pick",this.minecraft.options.pletzelEasyPick);
                toggle(right,y,"Easy Place",this.minecraft.options.pletzelEasyPlace);
            });
            rows.add(y->{
                add(left,y,"Position / Transform",()->selectPanel(1));
                add(right,y,"Layer Controls",()->selectPanel(2));
            });
            rows.add(y->{
                add(left,y,"Advanced Settings",()->selectPanel(3));
                this.addRenderableWidget(Button.builder(
                    Component.literal(this.minecraft.options.pletzelEasyPlaceHover.get()
                        ?"Easy Place Mode: Hover":"Easy Place Mode: Hold"),
                    button->{
                        boolean next=!this.minecraft.options.pletzelEasyPlaceHover.get();
                        this.minecraft.options.pletzelEasyPlaceHover.set(next);
                        this.minecraft.options.save();
                        status=next?"Hover: aim at legal ghosts to use vanilla placement":
                            "Hold: aim at ghosts and hold your normal Place Block key";
                        System.out.println("[PletzelEasyPlace] MODE hover="+next);
                        this.rebuildWidgets();
                    }).bounds(right,y,buttonWidth,BUTTON_H).build());
            });
        } else if(panel==1) {
            rows.add(y->{
                add(left,y,"Move X +",()->SchematicaSession.move(1,0,0));
                add(right,y,"Move Y +",()->SchematicaSession.move(0,1,0));
            });
            rows.add(y->{
                add(left,y,"Move Z +",()->SchematicaSession.move(0,0,1));
                add(right,y,"Move to Player",()->{
                    if(this.minecraft.player!=null)
                        SchematicaSession.setOrigin(this.minecraft.player.blockPosition());
                });
            });
            rows.add(y->{
                add(left,y,"Rotate 90 degrees",SchematicaSession::rotate);
                add(right,y,"Mirror X",SchematicaSession::mirrorX);
            });
            rows.add(y->{
                add(left,y,"Mirror Z",SchematicaSession::mirrorZ);
                add(right,y,"Reset Placement",SchematicaSession::resetPlacement);
            });
            rows.add(y->{
                add(left,y,"Layer Controls",()->selectPanel(2));
                add(right,y,"Back to Schematic",()->selectPanel(0));
            });
        } else if(panel==2) {
            rows.add(y->{
                add(left,y,"Layer Mode",SchematicaSession::cycleLayers);
                add(right,y,"Layer Up",SchematicaSession::layerUp);
            });
            rows.add(y->{
                add(left,y,"Layer Down",SchematicaSession::layerDown);
                add(right,y,"Back to Schematic",()->selectPanel(0));
            });
        } else {
            rows.add(y->{
                this.addRenderableWidget(Button.builder(
                    Component.literal(this.minecraft.options.pletzelEasyPlaceHover.get()
                        ?"Place Mode: Hover":"Place Mode: Hold"),
                    b->{
                        boolean hover=!this.minecraft.options.pletzelEasyPlaceHover.get();
                        this.minecraft.options.pletzelEasyPlaceHover.set(hover);
                        this.minecraft.options.save();
                        status=hover?"Hover: vanilla place only at valid targets":
                                     "Hold: use your normal Place Block binding";
                        this.rebuildWidgets();
                    }).bounds(left,y,buttonWidth,BUTTON_H).build());
                toggle(right,y,"Chunk Rendering",
                    this.minecraft.options.pletzelChunkRendering);
            });
            rows.add(y->{
                toggle(left,y,"Incremental Mesh",
                    this.minecraft.options.pletzelIncrementalMesh);
                toggle(right,y,"Wrong Highlight",
                    this.minecraft.options.pletzelWrongHighlight);
            });
            rows.add(y->{
                add(left,y,"Distance: Follow MC",()->
                    status="Render distance: "+this.minecraft.options.getEffectiveRenderDistance()+" chunks");
                add(right,y,"Wrong Color: Red",()->
                    status="Wrong blocks use complete red model faces");
            });
            rows.add(y->{
                add(left,y,"Placement Diagnostics",()->
                    status="Easy Place logs [PletzelEasyPlace] stages; no forged packets");
                add(right,y,"Back to Schematic",()->selectPanel(0));
            });
        }

        final int footerY=this.height-26;
        final int rowsPerPage=Math.max(1,
            (footerY-GAP-TOP-BUTTON_H)/PITCH+1);
        final int pages=Math.max(1,(rows.size()+rowsPerPage-1)/rowsPerPage);
        page=Math.min(page,pages-1);
        final int from=page*rowsPerPage;
        final int to=Math.min(rows.size(),from+rowsPerPage);
        for(int i=from;i<to;i++)rows.get(i).accept(TOP+(i-from)*PITCH);

        if(pages>1) {
            int width=Math.min(90,Math.max(40,(this.width-4*GAP)/3));
            int start=(this.width-(3*width+2*GAP))/2;
            this.addRenderableWidget(Button.builder(Component.literal("Prev Page"),b->{
                page=(page+pages-1)%pages;this.rebuildWidgets();
            }).bounds(start,footerY,width,BUTTON_H).build());
            this.addRenderableWidget(Button.builder(Component.literal("Done"),b->onClose())
                .bounds(start+width+GAP,footerY,width,BUTTON_H).build());
            this.addRenderableWidget(Button.builder(Component.literal("Next Page"),b->{
                page=(page+1)%pages;this.rebuildWidgets();
            }).bounds(start+2*(width+GAP),footerY,width,BUTTON_H).build());
        } else {
            this.addRenderableWidget(Button.builder(Component.literal("Done"),b->onClose())
                .bounds(this.width/2-Math.min(100,buttonWidth)/2,footerY,
                    Math.min(100,buttonWidth),BUTTON_H).build());
        }
    }

    @Override public void tick() {
        if(!choosing||!EagRuntime.fileChooserHasResult())return;
        choosing=false;
        try {
            FileChooserResult result=EagRuntime.getFileChooserResult();
            if(result==null||result.fileData==null) {
                status="File selection cancelled";return;
            }
            String filename=result.fileName==null?"":result.fileName;
            if(!filename.toLowerCase(java.util.Locale.ROOT)
                .matches(".*\\.(litematic|schematic|schem|nbt)$")) {
                status="Supported: .litematic, .schematic, .schem, .nbt";
                return;
            }
            SchematicaSession.loadAny(result.fileData,filename);
            System.out.println("[PletzelSchematicImport] LOADED "+filename+" "+
                SchematicaSession.width()+"x"+SchematicaSession.height()+"x"+
                SchematicaSession.length()+" cells="+SchematicaSession.cells().size());
            status="Loaded "+filename+" ("+SchematicaSession.width()+"x"+
                SchematicaSession.height()+"x"+SchematicaSession.length()+")";
            if(this.minecraft.player!=null)
                SchematicaSession.setOrigin(this.minecraft.player.blockPosition());
        } catch(IOException|RuntimeException exception) {
            status="Schematic loading failed: "+exception.getMessage();
            System.err.println("[PletzelSchematicImport] FAILED "+exception.getMessage());
        } finally {
            EagRuntime.clearFileChooserResult();
        }
    }

    @Override public void extractRenderState(GuiGraphicsExtractor graphics,int mouseX,
                                             int mouseY,float partialTicks) {
        super.extractRenderState(graphics,mouseX,mouseY,partialTicks);
        String heading=panel==0?"Schematic / Placement":panel==1?"Position / Transform":
            panel==2?"Layer Controls":"Advanced / Building";
        graphics.centeredText(this.font,Component.literal("Schematica — "+heading),
            this.width/2,5,0xffffffff);
        final int maxTextWidth=Math.max(60,this.width-24);
        String first=this.font.plainSubstrByWidth(status,maxTextWidth);
        String rest=status.substring(Math.min(status.length(),first.length())).trim();
        graphics.centeredText(this.font,Component.literal(first),this.width/2,17,0xffffffff);
        if(!rest.isEmpty())graphics.centeredText(this.font,Component.literal(
            this.font.plainSubstrByWidth(rest,maxTextWidth)),this.width/2,28,0xffffffff);
        if(SchematicaSession.loaded()) {
            var p=SchematicaSession.origin();
            String details=SchematicaSession.width()+"x"+SchematicaSession.height()+"x"+
                SchematicaSession.length()+" @ "+p.getX()+","+p.getY()+","+p.getZ()+
                (SchematicaSession.visible()?"  Hologram ON":"  Hologram OFF");
            graphics.centeredText(this.font,Component.literal(
                this.font.plainSubstrByWidth(details,maxTextWidth)),this.width/2,40,0xffaaffff);
        }
    }
    @Override public void onClose() { this.minecraft.gui.setScreen(parent); }
}
