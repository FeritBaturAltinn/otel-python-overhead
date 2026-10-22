import http from 'k6/http';

export const options = {
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  scenarios: {
    warmup: {
      executor: 'constant-vus', vus: 1, duration: '10s',
      tags: { phase: 'warmup' },
    },
    measure: {
      executor: 'constant-vus', vus: 1, duration: '30s', startTime: '10s',
      tags: { phase: 'measure' },
    },
  },
  thresholds: {
    // these dummy thresholds make k6 report the measure phase separately
    'http_req_duration{phase:measure}': ['max>=0'],
    'http_reqs{phase:measure}': ['count>=0'],
  },
};

export default function () {
  http.get(__ENV.TARGET);
}