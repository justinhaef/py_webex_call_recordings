from wxc_sdk import WebexSimpleApi

api = WebexSimpleApi()

results = api.converged_recordings.list_for_admin_or_compliance_officer(
    service_type="calling" # pyright: ignore[reportArgumentType]
    )
    
list = list(results)
print(len(list))

for recording in list:
    print(recording.id)

