import time
from smartz.api.constructor_engine import ConstructorInstance


class Constructor(ConstructorInstance):

    def get_version(self):
        return {
            "result": "success",
            "version": 2,
            "blockchain": "ethereum"
        }

    def get_params(self):
        json_schema = {
            "type": "object",
            "required": [
                "invoiceAmount", "beneficiary", "memo", "partialReceiver"
            ],

            "additionalProperties": True,

            "properties": {
                "invoiceAmount": {
                    "title": "Invoice Amount",
                    "description": "Ether amount which should be paid.",
                    "$ref": "#/definitions/ethCount"
                },

                "beneficiary": {
                    "title": "Beneficiary address",
                    "description": "Who will get money when the invoice is paid.",
                    "$ref": "#/definitions/address"
                },

                "memo": {
                    "title": "Short message",
                    "description": "What is the invoice for.",
                    "type": "string",
                    "minLength": 0,
                    "maxLength": 256
                },

                "autoWithdrawOnPaid": {
                    "title": "Auto send on paid",
                    "description": "Auto send funds to beneficiary if invoice become paid",
                    "type": "boolean",
                    "default": True
                },

                "payer": {
                    "title": "Payer address",
                    "description": "If this address is set, invoice can be paid only by it. All other receipts will be returned.",
                    "$ref": "#/definitions/address"
                },

                "validityPeriod": {
                    "title": "Valid Until",
                    "description": "After this date invoice will become invalid and send back all incoming Ether. If it was partially paid before this date, stored ether will become available for withdraw by payer or beneficiary depending on the following parameter value.",
                    "$ref": "#/definitions/unixTime"
                },

                "partialReceiver": {
                    "title": "Partial Receiver",
                    "description": "Who will withdraw funds from invoice contract in case it's validity period ended and it accumulated some funds on it.",
                    "type": "string",
                    "default": "Beneficiary",
                    "enum": ['Beneficiary', 'Payer'],
                },
            },

            "dependencies": {
                "partialReceiver": {
                    "oneOf": [{
                        "properties": {
                            "partialReceiver": {
                                "enum": ['Beneficiary']
                            }
                        },
                    }, {
                        "properties": {
                            "partialReceiver": {
                                "enum": ['Payer']
                            },
                        },
                        "required": ["payer"]
                    }]
                }
            }
        }

        ui_schema = {
            "ui:order": ["invoiceAmount", "beneficiary", "memo", "payer", "validityPeriod", "partialReceiver", "*"],

            "invoiceAmount": {
                "ui:widget": "ethCount",
            },
            "validityPeriod": {
                "ui:widget": "unixTime",
            },
            "partialReceiver": {
                "ui:widget": "radio",
            }
        }

        return {
            "result": "success",
            "schema": json_schema,
            "ui_schema": ui_schema
        }

    def construct(self, fields_vals):

        source = self.__class__._TEMPLATE

        if 'payer' not in fields_vals:
            fields_vals['payer'] = '0x00'
            source = source.replace('%payerVisibility%', 'internal')
        else:
            source = source.replace('%payerVisibility%', 'public')

        if 'validityPeriod' not in fields_vals:
            fields_vals['validityPeriod'] = 0
            source = source.replace('%validityPeriodVisibility%', 'internal')
        else:
            source = source.replace('%validityPeriodVisibility%', 'public')

        if fields_vals['partialReceiver'] == 'Beneficiary':
            fields_vals['partialReceiver'] = fields_vals['beneficiary']
        elif fields_vals['partialReceiver'] == 'Payer':
            fields_vals['partialReceiver'] = fields_vals['payer']
        else:
            return {
                "result": "error",
                "error_descr": "incorrect `partialReceiver`"
            }

        autoWithdrawOnPaidCode = ""
        if fields_vals['autoWithdrawOnPaid'] == True:
            autoWithdrawOnPaidCode = "doWithdraw(beneficiary, getBalance());"

        source = source \
            .replace('%invoiceAmount%', str(fields_vals['invoiceAmount'])) \
            .replace('%beneficiary%', fields_vals['beneficiary']) \
            .replace('%memo%', fields_vals['memo']) \
            .replace('%payer%', fields_vals['payer']) \
            .replace('%validityPeriod%', str(fields_vals['validityPeriod'])) \
            .replace('%partialReceiver%', fields_vals['partialReceiver']) \
            .replace('%autoWithdrawOnPaid%', autoWithdrawOnPaidCode)

        return {
            "result": "success",
            'source': source,
            'contract_name': "InvoiceWrapper"
        }

    def post_construct(self, fields_vals, abi_array):

        function_titles = {
            # VIEW functions
            'memo': {
                'title': 'Short Message',
                'description': 'What is the invoice for.',
                'sorting_order': 10
            },

            'invoiceAmount': {
                'title': 'Invoice Amount',
                'description': 'Ether amount which should be paid.',
                'ui:widget': 'ethCount',
                'sorting_order': 20
            },

            'paidAmount': {
                'title': 'Current Paid Amount',
                'description': 'Ether amount which currently paid.',
                'ui:widget': 'ethCount',
                'sorting_order': 30
            },

            'getStatus': {
                'title': 'Status',
                'description': 'Current invoice status.',
                'ui:widget': 'enum',
                'ui:widget_options': {
                    'enum': ['Active', 'Overdue', 'Paid']
                },
                'sorting_order': 40
            },

            'getBalance': {
                'title': 'Balance',
                'description': 'Ether amount which currently accumulated in contract.',
                'ui:widget': 'ethCount',
                'sorting_order': 50
            },

            'beneficiary': {
                'title': 'Beneficiary',
                'description': 'Who will get money when the invoice is paid.',
                'sorting_order': 60
            },

            'payer': {
                'title': 'Payer',
                'description': 'If this address is set, invoice can be paid only from it. All other receipts will be returned.',
                'sorting_order': 70
            },

            'validityPeriod': {
                'title': 'Valid Until',
                'description': 'After this date invoice contract will not accept incoming Ether and accumulated ether (if any) will become available for withdraw.',
                'ui:widget': 'unixTime',
                'ui:widget_options': {
                    'format': "yyyy.mm.dd HH:MM:ss (o)"
                },
                'sorting_order': 80
            },

            'partialReceiver': {
                'title': 'Partial Receiver',
                'description': 'Who will be able to withdraw funds from invoice contract after it validity period ends if partial funds accumulated but invoice amount is not collected.',
                'sorting_order': 90
            },

            # Write functions
            '': {
                'title': 'Pay',
                'description': 'Pay the invoice',
                'payable_details': {
                    'title': 'Ether amount',
                    'description': 'This ether amount will be sent to the invoice contract.'
                },
                'sorting_order': 100,
                'icon': {
                    'pack': 'materialdesignicons',
                    'name': 'arrow-right-bold'
                },
            },

            'withdraw': {
                'title': 'Withdraw',
                'description': 'Withdraw funds from invoice contract after it validity period ends if partial funds accumulated but invoice amount is not collected.',
                'sorting_order': 110,
                'inputs': [{
                    'title': 'Receiver Address',
                    'description': 'Who will receive ether.'
                }, {
                    'title': 'Ether Amount',
                    'description': 'This ether amount will be sent.',
                    'ui:widget': 'ethCount'
                }],
                'icon': {
                    'pack': 'materialdesignicons',
                    'name': 'arrow-left-bold'
                },
            },
        }

        return {
            "result": "success",
            'function_specs': function_titles,
            'dashboard_functions': ['memo', 'invoiceAmount', 'paidAmount', 'getStatus']
        }


    # language=Solidity
    _TEMPLATE = """
pragma solidity ^0.4.20;

library SafeMath {
  function mul(uint256 a, uint256 b) internal pure returns (uint256) {
    if (a == 0) {
      return 0;
    }
    uint256 c = a * b;
    assert(c / a == b);
    return c;
  }

  function div(uint256 a, uint256 b) internal pure returns (uint256) {
    // assert(b > 0); // Solidity automatically throws when dividing by 0
    uint256 c = a / b;
    // assert(a == b * c + a % b); // There is no case in which this doesn't hold
    return c;
  }

  function sub(uint256 a, uint256 b) internal pure returns (uint256) {
    assert(b <= a);
    return a - b;
  }

  function add(uint256 a, uint256 b) internal pure returns (uint256) {
    uint256 c = a + b;
    assert(c >= a);
    return c;
  }
}

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
    uint256 public paidAmount;
    uint256 %validityPeriodVisibility% validityPeriod;
    address public beneficiary;
    address %payerVisibility% payer;
    address public partialReceiver;
    string public memo;

    function Invoice (
        uint256 _invoiceAmount,
        string _memo,
        address _beneficiary,
        address _payer,
        uint256 _validityPeriod,
        address _partialReceiver
    ) public {
        require(_validityPeriod > now || _validityPeriod == 0);
        require(_partialReceiver == _payer || _partialReceiver == _beneficiary);

        invoiceAmount = _invoiceAmount;
        memo = _memo;
        beneficiary = _beneficiary;
        payer = _payer;
        validityPeriod = _validityPeriod;
        partialReceiver = _partialReceiver;
    }

    modifier onlyPayer() {
        require(payer == address(0) || msg.sender == payer);
        _;
    }

    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }

    function getStatus() public view returns (Status) {
        if (paidAmount == invoiceAmount)
            return Status.Paid;
        if (validityPeriod != 0 && now > validityPeriod)
            return Status.Overdue;
        return Status.Active;
    }

    function doRefund(uint256 amount) internal {
        msg.sender.transfer(amount);
        Refund(msg.sender, amount);
    }

    function doWithdraw(address receiver, uint256 amount) internal {
        receiver.transfer(amount);
        Withdraw(receiver, amount);
    }

    function () public payable onlyPayer {
        require(getStatus() == Status.Active);

        uint256 will = paidAmount.add(msg.value);

        if (will >= invoiceAmount) {
            if (will > invoiceAmount)
                doRefund(will - invoiceAmount);

            paidAmount = invoiceAmount;

            %autoWithdrawOnPaid%
        }
        else {
            paidAmount = will;
        }

        Payment(msg.sender, msg.value);
    }

    function withdraw(address receiver, uint256 amount) public {
        require(getBalance() >= amount);

        Status status = getStatus();

        require (
            (status == Status.Paid && msg.sender == beneficiary) ||
            (status == Status.Active && validityPeriod == 0 && msg.sender == partialReceiver) ||
            (status == Status.Overdue && msg.sender == partialReceiver)
        );

        doWithdraw(receiver, amount);
    }
}

contract InvoiceWrapper is Invoice(
    %invoiceAmount%,
    "%memo%",
    %beneficiary%,
    %payer%,
    %validityPeriod%,
    %partialReceiver%
) { }
    """
