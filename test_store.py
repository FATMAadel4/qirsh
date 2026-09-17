from store import build_transaction, append_transaction, get_all_transactions

test_user_id = "1523532707"

transaction = build_transaction(
    amount=150.0,
    category="Groceries",
    note="سوبر ماركت",
    transcript="صرفت مية وخمسين جنيه في السوبر ماركت",
    model="deepgram-nova-3",
)

append_transaction(test_user_id, transaction)

print("Reading back:")
for t in get_all_transactions(test_user_id):
    print(t)