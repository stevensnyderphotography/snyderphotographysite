#!/bin/bash
cd "$(dirname "$0")"
BRANCH=folder-galleries-draft
if [ "$(git branch --show-current)" != "$BRANCH" ]; then
  echo "This folder is not on the draft branch ($BRANCH), so nothing was sent."
  echo "Your live site is not affected."
  read -n 1 -s -r -p "Press any key to close."; exit 1
fi
echo "Updating galleries..."
python3 update-galleries.py
echo
echo "Saving your changes to the draft branch..."
git add photos/fundraisers photos/celebrations photos/music photos/community photos/wildlife photos/*.jpg site.json *.html js css update-galleries.py "Update Galleries.command"
git commit -m "Update draft: photos, order, tiles and top images" || echo "(nothing new to save)"
echo
echo "Sending the draft to GitHub (your live site is not changed)..."
git push -u origin $BRANCH
echo
echo "Done. Netlify will build a preview of the draft in a minute or two."
echo "Find it in Netlify > your site > Deploys (look for $BRANCH)."
echo
read -n 1 -s -r -p "Press any key to close."
