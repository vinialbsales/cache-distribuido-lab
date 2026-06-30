import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: Number(__ENV.VUS || 20),
  duration: __ENV.DURATION || "30s",
  summaryTrendStats: ["avg", "min", "med", "p(90)", "p(95)", "max"],
  thresholds: {
    http_req_failed: ["rate<0.02"],
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
  const roll = Math.random();
  let response;

  if (roll < 0.65) {
    response = http.get(`${BASE_URL}/products/${PRODUCT_ID}/cache`, {
      tags: { scenario: "mixed_load", operation: "cache_read" },
    });
  } else if (roll < 0.9) {
    response = http.get(`${BASE_URL}/products/${PRODUCT_ID}/no-cache`, {
      tags: { scenario: "mixed_load", operation: "db_read" },
    });
  } else {
    response = http.put(
      `${BASE_URL}/products/${PRODUCT_ID}`,
      JSON.stringify({
        name: "Notebook Benchmark",
        price: "4399.90",
        stock: Math.floor(Math.random() * 50) + 1,
      }),
      {
        headers: { "Content-Type": "application/json" },
        tags: { scenario: "mixed_load", operation: "update" },
      },
    );
  }

  check(response, {
    "status is 200": (r) => r.status === 200,
  });

  sleep(Number(__ENV.SLEEP || 1));
}
