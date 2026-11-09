// Runs before page scripts. The session stays in this closure, never web storage/URLs.
(() => {
  const origin = __ORIGIN__;
  if (window !== window.top || window.location.origin !== origin) return;
  const token = __TOKEN__;
  const nativeFetch = window.fetch.bind(window);
  Object.defineProperty(window, "fetch", { configurable: false, writable: false,
    value(input, init = {}) {
      const request = new Request(input, init);
      if (new URL(request.url).origin !== origin) return nativeFetch(request);
      const headers = new Headers(request.headers);
      headers.set("X-Desktop-Session", token);
      return nativeFetch(new Request(request, { headers, redirect: "error" }));
    }
  });
})();
