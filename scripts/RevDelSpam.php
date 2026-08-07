<?php
/**
 * One-off maintenance script: hide the text + edit summary of specific
 * revisions (RevisionDelete) so vandalism/spam content is suppressed from
 * public view (history, diffs) while keeping the revision record and
 * username attribution intact.
 *
 * Usage:
 *   php maintenance/run.php RevDelSpam.php \
 *     --title "Main Page" --ids 21903 --performer FightorderAdmin \
 *     --reason "Suppressing spam/malicious redirect content" [--dry-run]
 */

use MediaWiki\Revision\RevisionRecord;

// Run via `php maintenance/run.php <path>/RevDelSpam.php` — the runner
// autoloads the Maintenance base class before including this file, so no
// manual require is needed (and none would resolve correctly anyway,
// since this script lives outside the install tree).

class RevDelSpam extends Maintenance {
	public function __construct() {
		parent::__construct();
		$this->addDescription( 'Revision-delete (hide text+comment) of specific revisions on a page.' );
		$this->addOption( 'title', 'Page title', true, true );
		$this->addOption( 'ids', 'Comma-separated revision IDs', true, true );
		$this->addOption( 'performer', 'Username performing the action (needs deleterevision right)', true, true );
		$this->addOption( 'reason', 'Reason shown in the log', false, true );
		$this->addOption( 'dry-run', 'List targeted revisions without changing anything' );
	}

	public function execute() {
		$titleText = $this->getOption( 'title' );
		$ids = array_map( 'intval', explode( ',', $this->getOption( 'ids' ) ) );
		$reason = $this->getOption( 'reason', 'Suppressing spam/vandalism content' );
		$performerName = $this->getOption( 'performer' );

		$title = Title::newFromText( $titleText );
		if ( !$title || !$title->exists() ) {
			$this->fatalError( "Title not found: $titleText" );
		}

		$performer = User::newFromName( $performerName );
		if ( !$performer || !$performer->getId() ) {
			$this->fatalError( "Performer user not found: $performerName" );
		}

		if ( $this->hasOption( 'dry-run' ) ) {
			$this->output( "DRY RUN — would hide text+comment for revision(s) "
				. implode( ',', $ids ) . " on \"$titleText\"\n" );
			return;
		}

		$context = RequestContext::getMain();
		$context->setUser( $performer );

		$list = new RevDelRevisionList( $context, $title, $ids );

		$status = $list->setVisibility( [
			'value' => [
				RevisionRecord::DELETED_TEXT => 1,
				RevisionRecord::DELETED_COMMENT => 1,
			],
			'comment' => $reason,
		] );

		if ( $status->isGood() ) {
			$this->output( "Revision-deleted text+comment for id(s) "
				. implode( ',', $ids ) . " on \"$titleText\"\n" );
		} else {
			$this->fatalError( 'Failed: ' . $status->getWikiText( false, false, 'en' ) );
		}
	}
}

$maintClass = RevDelSpam::class;
require_once RUN_MAINTENANCE_IF_MAIN;
