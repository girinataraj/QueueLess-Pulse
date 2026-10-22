package io.github.girinataraj.queuelesspulse;

import com.getcapacitor.BridgeActivity;
import androidx.activity.OnBackPressedCallback;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.HttpAuthHandler;
import android.webkit.SslErrorHandler;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.net.http.SslError;
import android.content.Intent;
import android.print.PrintManager;
import android.widget.Toast;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import javax.net.ssl.HttpsURLConnection;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends BridgeActivity {
    private byte[] pendingQr;
    private BackendPolicy launchPolicy;
    private WebView appView;
    private final ExecutorService downloads = Executors.newSingleThreadExecutor();
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);
        WebView view = getBridge().getWebView();
        WebView.setWebContentsDebuggingEnabled(false);
        view.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        view.getSettings().setAllowFileAccess(false);
        view.getSettings().setAllowContentAccess(false);
        CookieManager.getInstance().setAcceptThirdPartyCookies(view, false);
        if (BuildConfig.BACKEND_ORIGIN.isEmpty()) return; // Honest offline installation-check flavor.
        BackendPolicy policy = new BackendPolicy(BuildConfig.BACKEND_ORIGIN);
        // Remote React needs no native plugins. Never expose a privileged JS bridge.
        view.removeJavascriptInterface("androidBridge");
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override public void handleOnBackPressed() {
                // Remote React deliberately has no Capacitor JS bridge. Handle
                // its normal WebView history and modal dismissal explicitly.
                view.evaluateJavascript("Boolean(document.querySelector('[role=dialog]'))", value -> {
                    if ("true".equals(value)) {
                        view.evaluateJavascript("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))", null);
                    } else if (view.canGoBack()) {
                        view.goBack();
                    } else {
                        finish();
                    }
                });
            }
        });
        view.setWebViewClient(new WebViewClient() {
            private boolean firstRemotePage = true;
            @Override public boolean shouldOverrideUrlLoading(WebView webView, WebResourceRequest request) {
                if (request.isForMainFrame() && request.getUrl().toString().equals(BuildConfig.BACKEND_ORIGIN+"/app/native-print")) {
                    PrintManager printer = (PrintManager)getSystemService(PRINT_SERVICE);
                    printer.print("QueueLess Pulse QR", webView.createPrintDocumentAdapter("QueueLess Pulse QR"), null);
                    return true;
                }
                String url = request.getUrl().toString();
                return request.isForMainFrame() ? !policy.allowsWebViewNavigation(url) : !policy.allows(url);
            }
            @Override public void onPageFinished(WebView webView, String url) {
                if (policy.launchEntry(url) != null && firstRemotePage) {
                    webView.clearHistory(); // Never go back to the internal installation screen.
                    firstRemotePage = false;
                }
                if (policy.launchEntry(url) != null) webView.evaluateJavascript(
                    "window.print=()=>{window.location.href='/app/native-print'};", null);
            }
            @Override public void onReceivedSslError(WebView webView, SslErrorHandler handler, SslError error) {
                handler.cancel(); // No certificate warning bypass or alternate trust store.
            }
            @Override public void onReceivedHttpAuthRequest(WebView webView, HttpAuthHandler handler, String host, String realm) {
                handler.cancel(); // Application sessions only; never prompt or send Basic credentials.
            }
        });
        view.setDownloadListener((url, agent, disposition, mime, length) -> {
            if (!policy.allowsQrDownload(url)) {
                Toast.makeText(this,"Only service QR downloads are allowed",Toast.LENGTH_LONG).show(); return;
            }
            final String cookie = CookieManager.getInstance().getCookie(url);
            downloads.execute(() -> {
                HttpsURLConnection connection = null;
                try {
                    connection = (HttpsURLConnection)new URL(url).openConnection();
                    connection.setInstanceFollowRedirects(false);
                    connection.setConnectTimeout(10000); connection.setReadTimeout(10000);
                    if (cookie != null) connection.setRequestProperty("Cookie",cookie);
                    if (connection.getResponseCode()!=200 || !"image/png".equals(connection.getContentType())) throw new java.io.IOException("QR not available");
                    ByteArrayOutputStream buffer = new ByteArrayOutputStream();
                    try (InputStream input=connection.getInputStream()) {
                        byte[] chunk=new byte[4096]; int count;
                        while ((count=input.read(chunk))!=-1) {
                            if (buffer.size()+count>1048576) throw new java.io.IOException("QR exceeds limit");
                            buffer.write(chunk,0,count);
                        }
                    }
                    byte[] qr=buffer.toByteArray();
                    if (qr.length<8 || qr[0]!=(byte)137 || qr[1]!=80 || qr[2]!=78 || qr[3]!=71) throw new java.io.IOException("Invalid PNG");
                    runOnUiThread(() -> {
                        pendingQr=qr;
                        Intent destination=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("image/png")
                            .addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"QueueLess-Service-QR.png");
                        startActivityForResult(destination,701);
                    });
                } catch (java.io.IOException error) {
                    runOnUiThread(() -> Toast.makeText(this,"QR download failed. Sign in to Reception and check your connection.",Toast.LENGTH_LONG).show());
                } finally { if (connection!=null) connection.disconnect(); }
            });
        });
        // BridgeActivity calls onNewIntent during super.onCreate. Publish these
        // fields only after every WebView security control and client is ready.
        launchPolicy = policy;
        appView = view;
        Intent initial = getIntent();
        String entry = policy.launchEntry(initial != null && Intent.ACTION_VIEW.equals(initial.getAction())
                ? initial.getDataString() : null);
        view.loadUrl(entry != null ? entry : policy.patientEntry());
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (launchPolicy == null || appView == null || intent == null
                || !Intent.ACTION_VIEW.equals(intent.getAction())) return;
        String entry = launchPolicy.launchEntry(intent.getDataString());
        if (entry == null) return; // Invalid later intents leave the current session and page intact.
        setIntent(intent);
        appView.loadUrl(entry); // Never log intent data or private ticket parameters.
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data) {
        super.onActivityResult(requestCode,resultCode,data);
        if (requestCode!=701) return;
        byte[] qr=pendingQr; pendingQr=null;
        if (resultCode!=RESULT_OK || data==null || data.getData()==null || qr==null) return;
        try (OutputStream output=getContentResolver().openOutputStream(data.getData())) {
            if (output==null) throw new java.io.IOException("No destination");
            output.write(qr);
            Toast.makeText(this,"Service QR saved",Toast.LENGTH_SHORT).show();
        } catch (java.io.IOException error) { Toast.makeText(this,"Could not save QR",Toast.LENGTH_LONG).show(); }
    }
    @Override public void onDestroy() {
        pendingQr=null; downloads.shutdownNow();
        super.onDestroy();
    }
}
