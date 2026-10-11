package io.github.girinataraj.queuelesspulse;

import static org.junit.Assert.*;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.security.NetworkSecurityPolicy;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class InstallationTest {
    @Test public void rendersHonestOfflineVerificationWithoutLoginFields() throws Exception {
        try (ActivityScenario<MainActivity> activity = ActivityScenario.launch(MainActivity.class)) {
            AtomicReference<String> body = new AtomicReference<>("");
            for (int attempt=0; attempt<40 && !body.get().contains("awaiting approval"); attempt++) {
                CountDownLatch evaluated = new CountDownLatch(1);
                activity.onActivity(a -> a.getBridge().getWebView().evaluateJavascript(
                    "JSON.stringify({text:document.body.innerText,inputs:document.querySelectorAll('input').length})",
                    result -> {body.set(result); evaluated.countDown();}));
                assertTrue(evaluated.await(5, TimeUnit.SECONDS));
                if (!body.get().contains("awaiting approval")) Thread.sleep(250);
            }
            assertTrue(body.get(),body.get().contains("awaiting approval"));
            assertTrue(body.get(),body.get().contains("inputs\\\":0"));
        }
    }
    @Test public void protectsScreenAndWebViewBoundaries() {
        try (ActivityScenario<MainActivity> activity = ActivityScenario.launch(MainActivity.class)) {
            activity.onActivity(a -> {
                WebView view = a.getBridge().getWebView();
                assertFalse(view.getSettings().getAllowFileAccess());
                assertFalse(view.getSettings().getAllowContentAccess());
                assertFalse(CookieManager.getInstance().acceptThirdPartyCookies(view));
                assertEquals(WebSettings.MIXED_CONTENT_NEVER_ALLOW,view.getSettings().getMixedContentMode());
                assertTrue((a.getWindow().getAttributes().flags & WindowManager.LayoutParams.FLAG_SECURE) != 0);
            });
        }
    }
    @Test public void disablesCleartextAndAccountBackup() {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        assertFalse(NetworkSecurityPolicy.getInstance().isCleartextTrafficPermitted("example.com"));
        assertEquals(0,context.getApplicationInfo().flags & ApplicationInfo.FLAG_ALLOW_BACKUP);
    }
}
