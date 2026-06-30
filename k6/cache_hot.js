import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: Number(__ENV.VUS || 20),
  duration: __ENV.DURATION || "30s",
  summaryTrendStats: ["avg", "min", "med", "p(90)", "p(95)", "max"],
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const PRODUCT_ID = __ENV.PRODUCT_ID || "1";

export function setup() {
  const response = http.get(`${BASE_URL}/products/${PRODUCT_ID}/cache`);
  check(response, {
    "cache warmup returned 200": (r) => r.status === 200,
  });
}

export default function () {
  const response = http.get(`${BASE_URL}/products/${PRODUCT_ID}/cache`, {
    tags: { scenario: "cache_hot" },
  });

  check(response, {
    "status is 200": (r) => r.status === 200,
    "cache status is hit": (r) => r.json("cache_status") === "HIT",
  });

  sleep(Number(__ENV.SLEEP || 1));
}
