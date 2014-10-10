copy ( WITH RECURSIVE recursetree(id, name, parent_id, note, type, ponderation, state, path) AS (
    SELECT 
        id,
        name, 
        parent_id,
        note,
        type,
        ponderation,
        state, 
        array[id] AS path
    FROM comparison_factor WHERE parent_id is null
  UNION ALL
    SELECT t.id, t.name, t.parent_id, t.note, t.type, t.ponderation, t.state, rt.path || t.id
    FROM comparison_factor t
    JOIN recursetree rt ON rt.id = t.parent_id
  )
SELECT 'factor_'||id, name, 'factor_'||parent_id, note, type, ponderation, state FROM recursetree ORDER BY path
) to '/tmp/comparison_factor.csv' with csv;
