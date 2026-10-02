/* Category structure data: category and entry types */

const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");
const { getMedia } = require("./media");

// The default category, and a map of category cl name to filename in Resources/Changelog
const ChangelogsDir = path.resolve(__dirname, "../../Resources/Changelog");
const MainCategory = "AMBERFALL";
const MainCategoryPath = path.resolve(__dirname, "../..",
    process.env.CHANGELOG_DIR || "Resources/Changelog/AmberfallChangelog.yml");
const CategoryPaths = {
	[MainCategory]: MainCategoryPath,
	TRAUMA: "TraumaChangelog.yml",
	WIZDEN: "Changelog.yml",
    WIZDENADMIN: "Admin.yml",
    MAPS: "Maps.yml",
    ADMIN: "TraumaAdmin.yml",
    RULES: "Rules.yml",
};

// All allowed entry types and the final string to use in the changelog yml
const AllowedEntries = {
	add: "Add",
	remove: "Remove",
	tweak: "Tweak",
	fix: "Fix",
	bugfix: "Fix", // never seen anyone use these 2 but its SS14.Changelog parity
	bug: "Fix",
};
const FallbackEntryType = "Tweak";

// Returns true if a category is present in CategoryPaths, thus exists
function categoryExists(category) {
	return CategoryPaths[category] !== undefined;
}

// Options for saving the changelog yml files
const YamlOptions = { indent: 2, noArrayIndent: true };

// Regexes
const HeaderRegex = /^[\t ]*(?::cl:|🆑)[\t ]*([^\r\n]*)\r?\n([\s\S]*)/im;
const LineRegex = /\r?\n/;
const CategoryRegex = /^([a-zA-Z]+)\s*:/;
const EntryRegex = /^ *[*-]? *(add|remove|tweak|fix|bugfix|bug): *([^\n\r]+)\r?$/i;
const CommentRegex = /<!--.*?-->/gs; // HTML comments

// Main function
async function main() {
    const prnum = process.env.PR_NUMBER;
    if (prnum === undefined)
    	throw new Error(`Run from an action`);

	const repo = process.env.GITHUB_REPOSITORY;
    const prUrl = `https://github.com/${repo}/pull/${prnum}`;

    // Get PR details
	const uri = `https://api.github.com/repos/${repo}/pulls/${prnum}`;
	const token = process.env.GITHUB_TOKEN;
	const req = {
    	headers: {
    		Accept: 'application/vnd.github+json'
		}
	};
	if (token !== undefined)
		req.headers.Authorization = "Bearer " + token;
    const res = await fetch(uri, req);
	if (!res.ok)
		throw new Error(`Failed to fetch PR information for #${prnum}: ${res.status}`);

    const { merged_at, body, user, number, html_url } = await res.json();

    // Time is something like 2021-08-29T20:00:00Z
    // Time should be something like 2023-02-18T00:00:00.0000000+00:00
    let time = merged_at;
    if (!time) {
        console.log("Pull request was not merged, skipping");
        return;
    }

    time = time.replace("z", ".0000000+00:00").replace("Z", ".0000000+00:00");

    // Remove comments from the body
    const commentlessBody = (body || "").replace(CommentRegex, '');

    // Get author
    const headerMatch = HeaderRegex.exec(commentlessBody);
    if (!headerMatch) {
        console.log("No changelog entry found, skipping");
        return;
    }

    let author = headerMatch[1].trim();
    if (!author) {
        console.log("No author found, setting it to author of the PR\n");
        author = user.login;
    }

    // Get all changes from the changelog body
    const changelog = headerMatch[2];
    const entries = getChanges(changelog);
    if (entries === null)
    	return;

    const media = getMedia(body);

    // Construct changelog yml entries
    // Write changelogs
    for (const category in entries)
    {
    	const changes = entries[category];
	    const filePath = path.resolve(ChangelogsDir, CategoryPaths[category]);
	    const entry = {
	        author: author,
	        changes: changes,
	        id: -1, // set inside writeChangelog
	        time: time,
	        prNumber: number || Number(prnum),
	        url: html_url || prUrl,
	        ...(media.length ? { media } : {})
	    };
	    writeChangelog(filePath, entry);
    }

    console.log(`Changelog updated with changes from PR #${prnum}`);
}


// Code chunking

// Get all changes from the PR body
function getChanges(body) {
    const entries = {};
    let category = MainCategory;
    let empty = true;

    for (const line of body.split(LineRegex)) {
    	if (line === "")
    		continue;

        const match = EntryRegex.exec(line);
        if (match !== null) {
            (entries[category] ??= []).push({
                type: match[1].toLowerCase(), message: match[2].trim()
            });
            empty = false;
            continue;
        }

    	const matchedCat = CategoryRegex.exec(line);
    	if (matchedCat !== null) {
    		const name = matchedCat[1].toUpperCase();
    		if (!categoryExists(name))
    		{
    			console.log("Invalid changelog category:", name);
    			continue;
			}

    		category = name;
    		continue;
    	}

        console.log("Invalid line in changelog:", line);
    }

    if (empty)
    {
        console.log("No changes found, skipping");
        return null;
    }

    // Check change types to finish the entries
    for (const category in entries) {
    	const changes = entries[category];
    	for (const entry of changes) {
    		// map dev-facing string to the yml entry string
    		entry.type = AllowedEntries[entry.type] ?? FallbackEntryType;
        }
    }

    return entries;
}

// Get the highest changelog number from a list of entries
function getHighestCLNumber(entries) {
    let max = 0;
    for (const entry of entries) {
    	const id = entry.id;
    	if (id > max)
    		max = id;
	}

	return max;
}

// Append a changelog entry to a given file
function writeChangelog(path, entry) {
    const data = fs.existsSync(path)
        ? yaml.load(fs.readFileSync(path, "utf8"))
        : { Name: "Amberfall", Order: -3, Entries: [] };

    if (data.Entries.some(existing => existing.url === entry.url)) {
        console.log(`PR already present in ${path}, skipping`);
        return;
    }

	entry.id = getHighestCLNumber(data.Entries) + 1;

    data.Entries.push(entry);

    // Write updated changelogs file
    fs.writeFileSync(
        path,
        yaml.dump(data, YamlOptions).replace(/^---/, "")
    );
}

// Run main
if (require.main === module) {
    main().catch(error => {
        console.error(error);
        process.exitCode = 1;
    });
}

module.exports = { main, getChanges, writeChangelog };
