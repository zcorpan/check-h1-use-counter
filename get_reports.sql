SELECT
  metrics.url2. broken_site_report_url AS url,
  metrics.text2.broken_site_report_description AS description,
  document_id,
  normalized_channel AS firefox_channel,
  metadata.user_agent.version AS firefox_version,
  metadata.user_agent.os AS os,
  normalized_os_version AS os_version,
  normalized_country_code AS country,
  submission_timestamp
FROM
  `moz-fx-data-shared-prod.firefox_desktop.broken_site_report`
WHERE
  TIMESTAMP_TRUNC(submission_timestamp, DAY) >= TIMESTAMP("2025-03-22")
  AND EXISTS (
    SELECT
      1
    FROM
      UNNEST(ping_info.experiments) AS experiment
    WHERE
      experiment.key LIKE "%remove-ua-styles-for-h1-headings%"
      OR metrics.boolean.broken_site_report_browser_info_prefs_h1_in_section_useragent_styles_enabled = FALSE
  )
ORDER BY
  submission_timestamp DESC
