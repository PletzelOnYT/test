package net.pletzel.voice;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.Base64;
import java.util.concurrent.atomic.AtomicBoolean;

/** Server-authoritative Pletzel voice identity and position publisher. No game packets or voice audio. */
public final class PletzelVoicePlugin extends JavaPlugin implements Listener {
    private HttpClient http;
    private String gateway, secret, publicUrl, serverId;
    private final SecureRandom random = new SecureRandom();
    private final AtomicBoolean sending = new AtomicBoolean(false);

    @Override public void onEnable() {
        saveDefaultConfig();
        gateway = getConfig().getString("admin_url", "http://127.0.0.1:25580");
        secret = getConfig().getString("admin_secret", "");
        publicUrl = getConfig().getString("public_voice_url", "wss://voice.example.com/voice");
        serverId = getConfig().getString("server_id", "pletzel-server");
        if (secret == null || secret.length() < 32 || secret.contains("REPLACE-") ||
            !gateway.startsWith("http://127.0.0.1:") && !gateway.startsWith("https://")) {
            getLogger().severe("Voice disabled: set a 32+ char admin_secret and a secure/loopback admin_url in config.yml");
            getServer().getPluginManager().disablePlugin(this);
            return;
        }
        http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
        getServer().getPluginManager().registerEvents(this, this);
        getServer().getScheduler().runTaskTimer(this, this::snapshot, 1L, 5L);
        getLogger().info("Pletzel Voice identity / authoritative position service enabled. Browser audio remains opt-in.");
    }

    private void post(String path, String json, java.util.function.Consumer<Boolean> callback) {
        HttpRequest req=HttpRequest.newBuilder(URI.create(gateway+path))
            .timeout(Duration.ofSeconds(3))
            .header("Content-Type", "application/json")
            .header("X-Pletzel-Admin", secret)
            .POST(HttpRequest.BodyPublishers.ofString(json,StandardCharsets.UTF_8)).build();
        http.sendAsync(req,HttpResponse.BodyHandlers.discarding())
            .whenComplete((resp, err)->{
                boolean ok=err==null && resp.statusCode()==200;
                if (callback!=null && isEnabled()) {
                    Bukkit.getScheduler().runTask(this,()->callback.accept(ok));
                }
            });
    }

    private void snapshot() {
        if(!sending.compareAndSet(false,true)) return;
        JsonObject payload=new JsonObject();payload.addProperty("server",serverId);
        JsonArray players=new JsonArray();
        for(Player p:Bukkit.getOnlinePlayers()) {
            if(!p.isOnline())continue;
            Location l=p.getLocation();
            JsonObject a=new JsonObject();
            a.addProperty("id",p.getUniqueId().toString());
            a.addProperty("name",p.getName());
            a.addProperty("world",l.getWorld().getUID().toString());
            a.addProperty("x",l.getX());a.addProperty("y",l.getY());a.addProperty("z",l.getZ());
            players.add(a);
        }
        payload.add("players",players);
        post("/admin/snapshot",payload.toString(),ok->sending.set(false));
    }

    @EventHandler public void onQuit(PlayerQuitEvent e) {
        // Keep player removal server-authoritative without relying on client close.
        Bukkit.getScheduler().runTaskLater(this,this::snapshot,1L);
    }

    @Override public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if(!(sender instanceof Player p)) {
            sender.sendMessage("This command must be run as an authenticated in-game player.");return true;
        }
        if(args.length!=1 || !args[0].equalsIgnoreCase("token")) {
            p.sendMessage("§ePletzel Voice: §7use /pvoice token, then paste token into V menu. Voice URL: "+publicUrl);
            return true;
        }
        byte[] bytes=new byte[32];random.nextBytes(bytes);
        String token=Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        JsonObject grant=new JsonObject();grant.addProperty("id",p.getUniqueId().toString());grant.addProperty("token",token);
        post("/admin/grant",grant.toString(),ok->{
            if(!p.isOnline())return;
            if(!ok){p.sendMessage("§cVoice gateway not ready. Contact the server owner.");return;}
            p.sendMessage("§aPletzel Voice authorization (single-use; valid 75 seconds):");
            p.sendMessage("§e"+token);
            p.sendMessage("§7Press V, enter voice URL: "+publicUrl+", paste the token, then Enable Voice. Never share your token.");
        });
        return true;
    }

    @Override public void onDisable(){
        // When a server exits, the gateway also expires snapshots after 3.5s.
        sending.set(false);
    }
}