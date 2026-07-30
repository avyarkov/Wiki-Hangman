-- Distinct players active in the last 7 days
select count(distinct player_id) from completions where created_at > now() - interval '7 days';

-- Everything one player has played
select difficulty, title, won, letters_guessed, strikes, created_at
from completions
where player_id = '<uuid>'
order by created_at desc;
