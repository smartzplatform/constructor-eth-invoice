pragma solidity ^0.4.20;

import "../node_modules/openzeppelin-solidity/contracts/math/SafeMath.sol";

contract Invoice {
    using SafeMath for uint256;

    enum Status { Active, Overdue, Paid }

    event Refund(
        address receiver,
        uint256 amount
    );

    event Payment(
        address from,
        uint256 amount
    );

    event Withdraw(
        address receiver,
        uint256 amount
    );

    uint256 public invoiceAmount;
    uint256 public currentAmount;
    uint256 public validityPeriod;
    address public beneficiary;
    address public payer;
    address public partialReceiver;
    string public memo;
    address public owner;

    bool internal wasPaid;

    constructor (
        uint256 _invoiceAmount,
        string _memo,
        address _beneficiary,
        address _payer,
        uint256 _validityPeriod,
        address _partialReceiver
    ) public {
        if (_validityPeriod != 0) {
            require(_validityPeriod > now);
            require(_partialReceiver == _payer || _partialReceiver == _beneficiary);
        }

        invoiceAmount = _invoiceAmount;
        memo = _memo;
        beneficiary = _beneficiary;
        payer = _payer;
        validityPeriod = _validityPeriod;
        partialReceiver = _partialReceiver;
        owner = msg.sender;
    }

    modifier onlyPayer() {
        require(payer == address(0) || msg.sender == payer);
        _;
    }

    function getStatus() public view returns (Status) {
        if (wasPaid == true)
            return Status.Paid;
        if (validityPeriod != 0 && now > validityPeriod)
            return Status.Overdue;
        return Status.Active;
    }

    function doRefund(uint256 amount) internal {
        msg.sender.transfer(amount);
        emit Refund(msg.sender, amount);
    }

    function doWithdraw(address receiver, uint256 amount) internal {
        receiver.transfer(amount);
        emit Withdraw(receiver, amount);
    }

    function () public payable onlyPayer {
        require(getStatus() == Status.Active);

        uint256 will = currentAmount.add(msg.value);

        if (will >= invoiceAmount) {
            if (will > invoiceAmount)
                doRefund(will - invoiceAmount);
            currentAmount = invoiceAmount;
            wasPaid = true;
        }
        else {
            currentAmount = will;
        }

        emit Payment(msg.sender, msg.value);
    }

    function withdraw(address receiver, uint256 amount) public {
        require(currentAmount >= amount);

        Status status = getStatus();

        require (
            (status == Status.Paid && msg.sender == beneficiary) ||
            (status == Status.Overdue && msg.sender == partialReceiver)
        );

        doWithdraw(receiver, amount);

        currentAmount = currentAmount.sub(amount);
    }
}

