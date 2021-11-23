Change Log
==========

1.2.0 (unreleased)
------------------

* Updated ``LintTask`` to include a step for running Django system checks.
* Updated ``UpdateTask`` to use Django 3.1's command to detect unapplied migrations.
* Improved ``TaskProxy`` to allow better handling of errors in nested tasks.

1.1.1 (2021-07-16)
------------------

* Fixed bug in ``TaskProxy`` when generating a task description, causing the standalone ``jog`` command (called with no arguments) to crash.

1.1.0 (2021-07-14)
------------------

* String-based and function-based tasks now use the same mechanism for executing commands on the command line as task-based classes. This allows these types of tasks to accept ``--stdout`` and ``--stderr`` arguments to allow output stream redirection.

1.0.1 (2021-07-01)
------------------

* Fixed bug where argument parsing would fail when calling a task without arguments from within another.
* Improved display of help text in various scenarios.

1.0.0 (2021-06-03)
------------------

* Initial release
