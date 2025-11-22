from unittest.mock import patch, MagicMock

from utils.adapters.unit_of_work import UnitOfWork


@patch("utils.adapters.unit_of_work.transaction")
def test_uow_context_manager(mock_transaction):
    """
    GIVEN a UnitOfWork instance
    WHEN it is used as a context manager
    THEN it should enter and exit the transaction context
    """
    uow = UnitOfWork(using="default", savepoint=True, durable=False)

    with uow:
        mock_transaction.set_autocommit.assert_called_once_with(False)

    mock_transaction.set_autocommit.assert_called_with(True)


@patch("utils.adapters.unit_of_work.transaction")
def test_uow_commit(mock_transaction):
    """
    GIVEN a UnitOfWork instance
    WHEN the commit method is called
    THEN it should call transaction.commit
    """
    uow = UnitOfWork(using="default")
    uow.commit()
    mock_transaction.commit.assert_called_once_with("default")


@patch("utils.adapters.unit_of_work.transaction")
def test_uow_rollback(mock_transaction):
    """
    GIVEN a UnitOfWork instance
    WHEN the rollback method is called
    THEN it should call transaction.rollback
    """
    uow = UnitOfWork(using="another_db")
    uow.rollback()
    mock_transaction.rollback.assert_called_once_with("another_db")
