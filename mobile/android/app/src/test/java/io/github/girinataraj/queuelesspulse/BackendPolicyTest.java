package io.github.girinataraj.queuelesspulse;

import org.junit.Test;
import static org.junit.Assert.*;

public class BackendPolicyTest {
    private final BackendPolicy policy = new BackendPolicy("https://approved.onrender.com");
    @Test public void acceptsOnlySameHttpsOrigin() {
        assertTrue(policy.allows("https://approved.onrender.com/app/b/erode/service/1"));
        assertTrue(policy.allows("https://approved.onrender.com:443/api/v1/session"));
        assertFalse(policy.allows("http://approved.onrender.com/app/"));
        assertFalse(policy.allows("https://approved.onrender.com:5001/app/"));
    }
    @Test public void rejectsCredentialTricksAndForeignOrigins() {
        for (String value : new String[]{"https://approved.onrender.com@evil.com/", "https://user@approved.onrender.com/",
                "https://approved.onrender.com.evil.com/", "https://evil.com/", "javascript:alert(1)", "file:///secret", "intent://evil", "not a URI"}) {
            assertFalse(value, policy.allows(value));
        }
    }
    @Test public void restrictsAuthenticationChallenge() {
        assertTrue(policy.allowsChallenge("approved.onrender.com", "QueueLess Pulse restricted demo"));
        assertFalse(policy.allowsChallenge("evil.com", "QueueLess Pulse restricted demo"));
        assertFalse(policy.allowsChallenge("approved.onrender.com", "Other realm"));
    }
    @Test public void downloadRequiresAuthorizedQrEndpointAtPinnedOrigin() {
        assertTrue(policy.allowsQrDownload("https://approved.onrender.com/api/v1/staff/services/1/qr.png?download=1"));
        assertTrue(policy.allowsQrDownload("https://approved.onrender.com/owner/business/1/qr.png?ui=react"));
        assertFalse(policy.allowsQrDownload("https://evil.com/api/v1/staff/services/1/qr.png"));
        assertFalse(policy.allowsQrDownload("https://approved.onrender.com/api/v1/session"));
        assertFalse(policy.allowsQrDownload("https://approved.onrender.com/arbitrary/qr.png"));
    }
    @Test public void refusesInvalidConfiguration() {
        for (String value : new String[]{"", "http://approved.onrender.com", "https://127.0.0.1", "https://demo.local",
                "https://queueless-pulse-demo.onrender.com", "https://approved.onrender.com/app/", "https://approved.onrender.com?secret=x", "https://user:password@approved.onrender.com"}) {
            try { new BackendPolicy(value); fail(value); } catch (IllegalArgumentException expected) { /* fail closed */ }
        }
    }
}
