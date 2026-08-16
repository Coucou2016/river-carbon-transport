# East River / WQP data fetch helper (optional R path)
# Primary pipeline uses src/01_fetch_water_quality.py
#
# Install: install.packages(c("httr", "readr"))
# Usage: Rscript src/01_fetch_water_quality.R

args <- commandArgs(trailingOnly = TRUE)
config_path <- if (length(args) > 0) args[1] else "configs/east_river.yaml"

message("R fetch stub — run Python fetch for full pipeline:")
message("  python run_pipeline.py")
message("Config: ", config_path)

resources <- c(
  east_river = "9f907b46baa848e180c49339d605bf31",
  dic_supplement = "2a2132999fb84214aad0596783812db2"
)

out_dir <- "data_raw/east_river"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

if (requireNamespace("httr", quietly = TRUE)) {
  for (nm in names(resources)) {
    rid <- resources[[nm]]
    url <- paste0("https://www.hydroshare.org/resource/", rid, "/")
    sub <- file.path(out_dir, nm)
    dir.create(sub, showWarnings = FALSE)
    tryCatch({
      resp <- httr::GET(url, httr::timeout(30))
      writeLines(substr(httr::content(resp, "text"), 1, 50000),
                 file.path(sub, paste0("hydroshare_", rid, "_landing.html")))
      message("Saved metadata: ", nm)
    }, error = function(e) message("Fetch failed: ", nm))
  }
}

message("Place HydroShare CSV exports in data_raw/east_river/ then re-run pipeline.")
