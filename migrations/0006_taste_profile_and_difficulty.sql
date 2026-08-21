-- Structured taste-profile fields (P5). Buttons are the primary editing UI;
-- body_text remains for freeform "in your own words" text and is the only
-- field the periodic rewrite job touches — effort/tags are direct user
-- selections and stay exactly as the user left them.
ALTER TABLE taste_profile ADD COLUMN effort TEXT NOT NULL DEFAULT '';
ALTER TABLE taste_profile ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]';

-- Recipe difficulty (P5, new feature request — display only for now).
ALTER TABLE recipe ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'intermediate';
