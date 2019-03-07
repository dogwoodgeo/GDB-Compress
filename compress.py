# # ###########################################################################
# # Script:       compress.py
# # Author:       Bradley Glenn Jones
# # Date:         January 11, 2016
# # Purpose:      Automates geodatabase compress
# # Inputs:       Uncompressed SDE geodatabase and versions
# # Outputs:      Compressed SDE geodatabase with rebuilt versions, indexes, and statistics
# # ###########################################################################

# Import modules
import arcpy
import time


from arcpy import env
env.workspace = r"C:\Users\-bjones\AppData\Roaming\ESRI\Desktop10.2\ArcCatalog\SDE@SQL1.sde"
env.overwriteOutput = True

# Set sde workspace
sdeWorkspace = env.workspace

# Variables
versionList = ["SEWERMAN.edits", "GISEDITOR.edits", "SDE.QC"]
sewerman = r"C:\Users\-bjones\AppData\Roaming\ESRI\Desktop10.2\ArcCatalog\SEWERMAN@SQL1.sde"
giseditor = r"C:\Users\-bjones\AppData\Roaming\ESRI\Desktop10.2\ArcCatalog\GISEDITOR@SQL1.sde"
sde = r"C:\Users\-bjones\AppData\Roaming\ESRI\Desktop10.2\ArcCatalog\SDE@SQL1.sde"


# Create a text file for logging
log = open("C:\\Geodatabase Compress\\CompressLog.txt", "a")
log.write("***************************************************************************************************\n")

# Define function for sending email.
def send_email(user, recipient, subject, body):
    import smtplib

    FROM = user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("172.21.1.147")
        server.sendmail(FROM, TO, message)
        server.close()
        log.write(str(time.asctime()) + ": Successfully sent email.\n")
    except:
        log.write(str(time.asctime()) + ": Failed to send email.\n")

# Error handling for majority of script
try:
    # Block new connections to the database.
    arcpy.AcceptConnections(sdeWorkspace, False)
    log.write(str(time.asctime()) + ": Database connections blocked.\n")

    # Get a list of database connections then disconnect users
    userList = arcpy.ListUsers(sdeWorkspace)
    log.write(str(time.asctime()) + ": " + str(userList))
    if len(userList) > 1:  # Always "1" connection because script initiates connection to the gdb
        log.write("\n" + str(time.asctime()) + ": There are " + str(len(userList) - 1) + " database connections.\n")
        arcpy.DisconnectUser(sdeWorkspace, "ALL")
        log.write(str(time.asctime()) + ": User(s) have been disconnected.\n")
    else:
        log.write("\n" + str(time.asctime()) + ": There are no connections to the geodatabase.\n")

    # Reconcile and post edits to dbo.DEFAULT.
    defaultWorkspace = r"C:\Users\-bjones\AppData\Roaming\ESRI\Desktop10.2\ArcCatalog\SDE@SQL1.sde"
    reconcileLog = r"C:\Geodatabase Compress\ReconcileLog.txt"
    arcpy.ReconcileVersions_management(defaultWorkspace,
                                       "ALL_VERSIONS",
                                       "sde.DEFAULT",
                                       versionList,
                                       "LOCK_ACQUIRED",
                                       "ABORT_CONFLICTS",
                                       "BY_OBJECT",
                                       "FAVOR_EDIT_VERSION",
                                       "POST",
                                       "KEEP_VERSION",
                                       reconcileLog)

    # Write lines of "reconcileLog" to "log"
    with open(reconcileLog, "r") as recFile:  # Open rec file
        for line in recFile:  # Iterate lines in rec file
            log.write(str(time.asctime()) + ": " + line)  # Write line to log file
    recFile.close()  # Close rec file

    # Compress gdb
    arcpy.Compress_management(defaultWorkspace)
    log.write(str(time.asctime()) + ": Geodatabase compressed.\n")

    # Delete versions
    for version in versionList:
        arcpy.DeleteVersion_management(defaultWorkspace, version)
        log.write(str(time.asctime()) + ": " + version + " version deleted.\n")

    # Compress gdb 2nd time
    arcpy.Compress_management(defaultWorkspace)
    log.write(str(time.asctime()) + ": Geodatabase compressed for second time.\n")

    # Allow the database to begin accepting connections again
    arcpy.AcceptConnections(defaultWorkspace, True)
    log.write(str(time.asctime()) + ": Database block removed.\n")

    # Rebuild versions
    connections = [sde, giseditor, sewerman]
    versions = ["QC", "edits", "edits"]
    pVersion = ["sde.Default", "SDE.QC", "SDE.QC"]
    fullNames = ["SDE.QC", "GISEDITOR.edits", "SEWERMAN.edits"]
    for i, versionName in enumerate(connections):
        arcpy.CreateVersion_management(connections[i], pVersion[i], versions[i], "PUBLIC")
        log.write(str(time.asctime()) + ": " + fullNames[i] + " version created.\n")

    # Rebuild indexes
    arcpy.RebuildIndexes_management(sewerman,
                                    "NO_SYSTEM",
                                    "SDE.SEWERMAN.MANHOLES_VIEW; "
                                    "SDE.SEWERMAN.SEWERS_VIEW; "
                                    "SDE.SEWERMAN.ProjectAreas; "
                                    "SDE.SEWERMAN.REPAVING",
                                    "ALL")
    log.write(str(time.asctime()) + ": Indexes rebuilt.\n")

    # Analyze datasets
    arcpy.AnalyzeDatasets_management(sewerman,
                                     "NO_SYSTEM",
                                     "SDE.SEWERMAN.MANHOLES_VIEW; "
                                     "SDE.SEWERMAN.SEWERS_VIEW; "
                                     "SDE.SEWERMAN.ProjectAreas; "
                                     "SDE.SEWERMAN.REPAVING",
                                     "ANALYZE_BASE",
                                     "NO_ANALYZE_DELTA",
                                     "ANALYZE_ARCHIVE")
    log.write(str(time.asctime()) + ": Analyze complete.\n")

    # Send "success" email.
    successSubj = "Script Completed"
    successContent = "Compress script completed"
    successPitcher = "Bradley.Jones@lrwu.com"
    successCatchers = "bradleyglennjones@gmail.com"
    send_email(successPitcher, successCatchers, successSubj, successContent)

except Exception, e:
    log.write(str(time.asctime()) + ": " + str(e) + "- Script failed to complete.\n")
    arcpy.AcceptConnections(sdeWorkspace, True)
    log.write(str(time.asctime()) + ": Database block removed.\n")
    # Send email to notify of script failure.
    subj = "Script Failure"
    content = "Compress script failed to complete: " + str(e)
    pitcher = "Bradley.Jones@lrwu.com"
    catchers = ["bradleyglennjones@gmail.com", "Mark.Drew@lrwu.com"]
    send_email(pitcher, catchers, subj, content)

log.close()
