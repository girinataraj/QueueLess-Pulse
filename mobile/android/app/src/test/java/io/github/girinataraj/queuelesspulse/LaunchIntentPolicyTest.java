package io.github.girinataraj.queuelesspulse;

import org.junit.Test;
import static org.junit.Assert.*;

/** The exact launch/redirect policy consumed by the connected WebView. */
public class LaunchIntentPolicyTest {
    private static final String ORIGIN = "https://queueless-pulse-staging-free.onrender.com";
    private final BackendPolicy policy = new BackendPolicy(ORIGIN);
    @Test public void retainsAllFiveRoleLaunchRoutes() {
        for (String path : new String[]{"/app", "/app/", "/app/b/erode-eye-clinic-demo/service/1",
                "/app/staff/login", "/app/staff/login?experience=reception", "/app/owner/login",
                "/app/b/erode-eye-clinic-demo/display"}) {
            assertEquals(ORIGIN+path, policy.launchEntry(ORIGIN+path));
        }
    }
    @Test public void keepsSameOriginAppQueryAndFragment() {
        String url=ORIGIN+"/app/owner/business/1?section=reviews&date=2026-10-14#main";
        assertEquals(url, policy.launchEntry(url));
    }
    @Test public void acceptsOnlyDefaultHttpsPort() {
        String url="https://queueless-pulse-staging-free.onrender.com:443/app/owner/login";
        assertEquals(url,policy.launchEntry(url));
        assertNull(policy.launchEntry("https://queueless-pulse-staging-free.onrender.com:5001/app/"));
    }
    @Test public void rejectsLookalikeAndNonAppPaths() {
        for(String path:new String[]{"", "/", "/application", "/appx/owner/login", "/api/v1/session", "/owner/login"}) {
            assertNull(path,policy.launchEntry(ORIGIN+path));
        }
    }
    @Test public void rejectsDotSegmentsAndEncodedPathSeparators() {
        for(String path:new String[]{"/app/../api/v1/session", "/app/./owner/login", "/app//owner/login",
                "/app/%2e%2e/api", "/app/%2E/owner", "/app/%2f%2fevil.com", "/app/%5cowner",
                "/app/%252e%252e/api", "/app/owner%00/login", "/app%2fowner/login", "/app/owner%3flogin"}) {
            assertNull(path,policy.launchEntry(ORIGIN+path));
        }
    }
    @Test public void rejectsHttpExternalHostsAndEmbeddedCredentials() {
        for(String url:new String[]{"http://queueless-pulse-staging-free.onrender.com/app/",
                "https://example.com/app/", "https://queueless-pulse-staging-free.onrender.com.evil.example/app/",
                "https://evil.queueless-pulse-staging-free.onrender.com/app/",
                "https://user:dummy@queueless-pulse-staging-free.onrender.com/app/",
                "https://queueless-pulse-staging-free.onrender.com@evil.example/app/",
                "https://queueless-pulse-staging-free.onrender.com./app/"}) {
            assertNull(policy.launchEntry(url));
        }
    }
    @Test public void rejectsMalformedRelativeAndUnsafeSchemes() {
        for(String url:new String[]{null, "", "not a URI", "/app/owner/login", "//queueless-pulse-staging-free.onrender.com/app/",
                "javascript:alert(1)", "file:///app/", "content://app/", "intent://app/", "data:text/html,hello",
                ORIGIN+"/app/%ZZ", ORIGIN+"\\app\\owner", ORIGIN+"/app/\nowner"}) {
            assertNull(policy.launchEntry(url));
        }
    }
    @Test public void protectedQrDownloadRetainsNavigationButIsNeverAnIntentDestination() {
        String qr=ORIGIN+"/api/v1/staff/services/1/qr.png?download=1";
        assertTrue(policy.allowsWebViewNavigation(qr));
        assertNull(policy.launchEntry(qr));
        assertFalse(policy.allowsWebViewNavigation("https://example.com/api/v1/staff/services/1/qr.png"));
        assertFalse(policy.allowsWebViewNavigation(ORIGIN+"/api/v1/session"));
        assertTrue(policy.allowsWebViewNavigation(ORIGIN+"/app/staff/reception"));
    }
    @Test public void redirectedNavigationUsesTheSameStrictBoundary() {
        assertNull(policy.launchEntry("https://example.com/app/owner/login"));
        assertNull(policy.launchEntry(ORIGIN+"/app/../api/v1/session"));
        assertEquals(ORIGIN+"/app/staff/reception",policy.launchEntry(ORIGIN+"/app/staff/reception"));
    }
}
