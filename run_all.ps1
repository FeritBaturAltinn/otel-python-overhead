$modes = "none", "noexport", "otlp"
$spans = 1, 5, 10, 50
$reps  = 5        # start with 1 to test; raise to 5 for the real run

New-Item -ItemType Directory -Force results | Out-Null
docker compose build

foreach ($rep in 1..$reps) {
  foreach ($mode in $modes) {
    foreach ($n in $spans) {
      $env:MODE  = $mode
      $env:SPANS = $n
      if ($mode -eq "otlp") { docker compose up -d app }
      else                  { docker compose up -d --no-deps app }
      Start-Sleep -Seconds 8
      docker compose run --rm k6 run --summary-export="/results/${mode}-${n}-${rep}.json" /scripts/load.js | Out-Null
      docker compose down
    }
  }
}