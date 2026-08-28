-- Read-only preflight for migration 0015. Review orphan identifiers under
-- the production data-retention policy; this script never changes data.

SELECT
    count(*) AS total_assets,
    count(*) FILTER (WHERE media_asset.visit_id IS NULL) AS null_visit_ids,
    count(*) FILTER (
        WHERE media_asset.visit_id IS NOT NULL AND visit.id IS NULL
    ) AS orphan_visit_ids
FROM operations.media_assets AS media_asset
LEFT JOIN operations.visits AS visit ON visit.id = media_asset.visit_id;

SELECT media_asset.id AS media_asset_id, media_asset.visit_id
FROM operations.media_assets AS media_asset
LEFT JOIN operations.visits AS visit ON visit.id = media_asset.visit_id
WHERE media_asset.visit_id IS NOT NULL
  AND visit.id IS NULL
ORDER BY media_asset.id;
