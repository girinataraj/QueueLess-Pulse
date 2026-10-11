package io.github.girinataraj.queuelesspulse;

import java.net.URI;
import java.net.URISyntaxException;

/** Exact HTTPS origin policy, with no caller-controlled backend switching. */
final class BackendPolicy {
    private final String hostname;
    BackendPolicy(String origin) {
        URI uri = parse(origin);
        if (uri == null || !secure(uri) || uri.getHost() == null
                || !uri.getHost().matches("[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\\.[a-z]{2,63}")
                || uri.getHost().endsWith(".local") || uri.getHost().endsWith(".internal")
                || uri.getHost().endsWith(".localhost")
                || uri.getHost().equals("queueless-pulse-demo.onrender.com")
                || (uri.getRawPath() != null && !uri.getRawPath().isEmpty())
                || uri.getRawQuery() != null || uri.getRawFragment() != null) {
            throw new IllegalArgumentException("An approved public HTTPS origin is required");
        }
        hostname = uri.getHost();
    }
    boolean allows(String url) {
        URI uri = parse(url);
        return uri != null && secure(uri) && hostname.equals(uri.getHost());
    }
    boolean allowsChallenge(String host, String realm) {
        return hostname.equals(host) && "QueueLess Pulse restricted demo".equals(realm);
    }
    boolean allowsQrDownload(String url) {
        URI uri = parse(url);
        return allows(url) && uri != null && uri.getPath().endsWith("/qr.png")
                && (uri.getPath().startsWith("/api/v1/staff/services/") || uri.getPath().startsWith("/owner/business/"));
    }
    private static boolean secure(URI uri) {
        return "https".equals(uri.getScheme()) && uri.getRawUserInfo() == null
                && (uri.getPort() == -1 || uri.getPort() == 443);
    }
    private static URI parse(String value) {
        try { return new URI(value); }
        catch (URISyntaxException | NullPointerException error) { return null; }
    }
}
