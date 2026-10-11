package io.github.girinataraj.queuelesspulse;

import com.getcapacitor.BridgeActivity;
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
import android.text.InputType;
import android.widget.EditText;
import android.widget.LinearLayout;
import androidx.appcompat.app.AlertDialog;
import android.content.Intent;
import android.print.PrintManager;
import android.widget.Toast;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import javax.net.ssl.HttpsURLConnection;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends BridgeActivity {
    private String invitationUser;
    private String invitationPassword;
    private byte[] pendingQr;
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
        view.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView webView, WebResourceRequest request) {
                if (request.isForMainFrame() && request.getUrl().toString().equals(BuildConfig.BACKEND_ORIGIN+"/app/native-print")) {
                    PrintManager printer = (PrintManager)getSystemService(PRINT_SERVICE);
                    printer.print("QueueLess Pulse QR", webView.createPrintDocumentAdapter("QueueLess Pulse QR"), null);
                    return true;
                }
                return !policy.allows(request.getUrl().toString());
            }
            @Override public void onPageFinished(WebView webView, String url) {
                if (policy.allows(url)) webView.evaluateJavascript(
                    "window.print=()=>{window.location.href='/app/native-print'};", null);
            }
            @Override public void onReceivedSslError(WebView webView, SslErrorHandler handler, SslError error) {
                handler.cancel(); // No certificate warning bypass or alternate trust store.
            }
            @Override public void onReceivedHttpAuthRequest(WebView webView, HttpAuthHandler handler, String host, String realm) {
                if (!policy.allowsChallenge(host, realm) || !policy.allows(webView.getUrl())) {
                    handler.cancel(); return;
                }
                LinearLayout fields = new LinearLayout(MainActivity.this);
                fields.setOrientation(LinearLayout.VERTICAL);
                int padding = (int)(24 * getResources().getDisplayMetrics().density);
                fields.setPadding(padding, padding, padding, padding);
                EditText user = new EditText(MainActivity.this);
                user.setHint("Private invitation username");
                user.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_NORMAL);
                EditText password = new EditText(MainActivity.this);
                password.setHint("Private invitation password");
                password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    user.setImportantForAutofill(android.view.View.IMPORTANT_FOR_AUTOFILL_NO);
                    password.setImportantForAutofill(android.view.View.IMPORTANT_FOR_AUTOFILL_NO);
                }
                fields.addView(user); fields.addView(password);
                new AlertDialog.Builder(MainActivity.this).setTitle("Restricted synthetic-data staging")
                    .setMessage("Use your private invitation for " + host + ".")
                    .setView(fields)
                    .setPositiveButton("Continue", (dialog, which) -> {
                        invitationUser = user.getText().toString();
                        invitationPassword = password.getText().toString();
                        handler.proceed(invitationUser, invitationPassword);
                        password.getText().clear();
                    })
                    .setNegativeButton("Cancel", (dialog, which) -> handler.cancel())
                    .setOnCancelListener(dialog -> handler.cancel()).show();
            }
        });
        view.setDownloadListener((url, agent, disposition, mime, length) -> {
            if (!policy.allowsQrDownload(url)) {
                Toast.makeText(this,"Only service QR downloads are allowed",Toast.LENGTH_LONG).show(); return;
            }
            final String cookie = CookieManager.getInstance().getCookie(url);
            final String user = invitationUser;
            final String password = invitationPassword;
            downloads.execute(() -> {
                HttpsURLConnection connection = null;
                try {
                    connection = (HttpsURLConnection)new URL(url).openConnection();
                    connection.setInstanceFollowRedirects(false);
                    connection.setConnectTimeout(10000); connection.setReadTimeout(10000);
                    if (cookie != null) connection.setRequestProperty("Cookie",cookie);
                    if (user != null && password != null) connection.setRequestProperty("Authorization", "Basic "+
                        android.util.Base64.encodeToString((user+":"+password).getBytes(StandardCharsets.UTF_8),android.util.Base64.NO_WRAP));
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
                    runOnUiThread(() -> Toast.makeText(this,"QR download failed. Check your invitation and connection.",Toast.LENGTH_LONG).show());
                } finally { if (connection!=null) connection.disconnect(); }
            });
        });
        view.loadUrl(BuildConfig.BACKEND_ORIGIN + "/app/");
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
        invitationUser=null; invitationPassword=null; pendingQr=null; downloads.shutdownNow();
        super.onDestroy();
    }
}
