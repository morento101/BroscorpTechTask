-- Топ 5 найпопулярніших статей (ті що мають найбільшу кількість посилань на себе)
SELECT title, COUNT(left_page_id)
FROM page_to_page JOIN page ON id = right_page_id
GROUP BY title
ORDER BY COUNT(left_page_id) DESC
LIMIT 5;


-- Топ 5 статей з найбільшою кількістю посилань на інші статті
SELECT title, COUNT(right_page_id)
FROM page_to_page JOIN page ON id = left_page_id
GROUP BY title
ORDER BY COUNT(right_page_id) DESC
LIMIT 5;


-- Для заданної статті знайти середню кількість потомків другого рівня
SELECT ROUND(AVG(count_child_depth_2), 0) AS avg_child_depth_2
FROM (
    SELECT COUNT(right_page_id) AS count_child_depth_2
    FROM page_to_page
    WHERE left_page_id IN (
        SELECT right_page_id
        FROM page JOIN page_to_page ON id = left_page_id
        WHERE title = 'Дружба'
    )
    GROUP BY left_page_id
) count_table;


-- (На додаткові бали) Запит, що має параметр - N, повертає до п’яти маршрутів переходу довжиною N. Сторінки в шляху не мають повторюватись.
