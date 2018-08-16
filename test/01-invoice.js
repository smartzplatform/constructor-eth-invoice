const expectThrow = require('../node_modules/openzeppelin-solidity/test/helpers/expectThrow').expectThrow;
const expectEvent = require('../node_modules/openzeppelin-solidity/test/helpers/expectEvent').expectEvent;

const BigNumber = web3.BigNumber;
const chai =require('chai');
chai.use(require('chai-bignumber')(BigNumber));
chai.use(require('chai-as-promised')); // Order is important
chai.should();

const zeroAddr = '0x0000000000000000000000000000000000000000';

const Invoice = artifacts.require("Invoice");

//const getBalance = (address) => new Promise((resolve, reject) => web3.eth.getBalance((err, res) => if (err) reject(err) else resolve(parseFloat(res.toString(10)))));
const now = () => ((new Date().getTime() / 1000) | 0);
const withDefault = (value, def) => (value === undefined || value === null) ? def : value;

async function passTime(time){
    await web3.currentProvider.send({
        jsonrpc: '2.0',
        method: 'evm_increaseTime',
        params: [time],
        id: new Date().getSeconds()
    }, async (err, resp) => {
        if (!err) {
            await web3.currentProvider.send({
                jsonrpc: '2.0',
                method: 'evm_mine',
                params: [],
                id: new Date().getSeconds()
            });
        }
    })
}

const contructorArgs = (args) => [
    withDefault(args.invoiceAmount, web3.toWei('1.0')),
    withDefault(args.memo, 'test invoice'),
    withDefault(args.beneficiary, zeroAddr),
    withDefault(args.payer, zeroAddr),
    withDefault(args.validityPeriod, 0),
    withDefault(args.partialReceiver, zeroAddr),
];

contract('Invoice - contructor', function(accounts) {
    const accts = {
        anyone: accounts[0],
        owner: accounts[1],
        beneficiary: accounts[2],
        payer: accounts[3],
    };

    const newInstance = async (args) => await Invoice.new(...contructorArgs(args), {from: accts.owner});

    it('0 validity period', async function() {
        let inst = await newInstance(Object.assign({}, accts));

        await inst.validityPeriod({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
    });

    it('Incorrect validity period', async function() {
        await expectThrow(newInstance(Object.assign({
            validityPeriod: now() - 60,
            partialReceiver: accts.beneficiary,
        }, accts)));
    });

    it('Incorrect partial receiver', async function() {
        await expectThrow(newInstance(Object.assign({
            validityPeriod: now() + 1,
            partialReceiver: accts.anyone,
        }, accts)));

        await expectThrow(newInstance(Object.assign({
            validityPeriod: now() + 60,
        }, accts)));
    });

    it('All fields', async function() {
        let args = {
            invoiceAmount: web3.toWei('101.00'),
            validityPeriod: now() + 60,
            payer: accts.payer,
            beneficiary: accts.beneficiary,
            partialReceiver: accts.payer,
            memo: 'some message',
        };

        let inst = await newInstance(args, accts);

        await inst.invoiceAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(args.invoiceAmount);
        await inst.beneficiary({from: accts.anyone}).should.eventually.be.equal(args.beneficiary);
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
        await inst.validityPeriod({from: accts.anyone}).should.eventually.be.bignumber.equal(args.validityPeriod);
        await inst.payer({from: accts.anyone}).should.eventually.be.equal(args.payer);
        await inst.partialReceiver({from: accts.anyone}).should.eventually.be.equal(args.partialReceiver);
        await inst.owner({from: accts.anyone}).should.eventually.be.equal(accts.owner);
        await inst.memo({from: accts.anyone}).should.eventually.be.equal(args.memo);

        await inst.getStatus({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
    });
});

contract('Invoice', function(accounts) {
    const accts = {
        anyone: accounts[0],
        owner: accounts[1],
        beneficiary: accounts[2],
        payer: accounts[3],
    };

    const newInstance = async (args) => await Invoice.new(...contructorArgs(args), {from: accts.owner});

    it('One pay', async function() {
        let invoiceAmount = web3.toWei('1.0');

        let inst = await newInstance(Object.assign({
            validityPeriod: now() + 60,
            partialReceiver: accts.beneficiary,
            invoiceAmount
        }, accts));

        await inst.sendTransaction({from: accts.payer, value: invoiceAmount});
        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(2);
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(invoiceAmount);
        assert.isOk(await inst.withdraw(accts.beneficiary, invoiceAmount, {from: accts.beneficiary}));
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
    });

    it('One pay with refund', async function() {
        let invoiceAmount = web3.toWei('1.0');

        let inst = await newInstance(Object.assign({
            validityPeriod: now() + 60,
            partialReceiver: accts.beneficiary,
            invoiceAmount
        }, accts));

        let payAmount = web3.toWei('1.1');

        await inst.sendTransaction({from: accts.payer, value: invoiceAmount});
        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(2);
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(invoiceAmount);
        assert.isOk(await inst.withdraw(accts.beneficiary, invoiceAmount, {from: accts.beneficiary}));
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
    });

    it('Many pays', async function() {
        let invoiceAmount = web3.toWei('1.0');

        let inst = await newInstance(Object.assign({
            validityPeriod: now() + 60,
            partialReceiver: accts.beneficiary,
            invoiceAmount
        }, accts));

        let payAmount = web3.toWei('0.2');

        for (let i = 0; i < 5; i++)
            await inst.sendTransaction({from: accts.payer, value: payAmount});

        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(2);
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(invoiceAmount);
        assert.isOk(await inst.withdraw(accts.beneficiary, invoiceAmount, {from: accts.beneficiary}));
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
    });

    it('Refund after full paid', async function() {
        let invoiceAmount = web3.toWei('1.0');

        let inst = await newInstance(Object.assign({
            validityPeriod: now() + 60,
            partialReceiver: accts.beneficiary,
            invoiceAmount
        }, accts));

        await inst.sendTransaction({from: accts.payer, value: invoiceAmount});
        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(2);
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(invoiceAmount);

        await expectThrow(inst.sendTransaction({from: accts.payer, value: invoiceAmount}));
        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(2);
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(invoiceAmount);

        assert.isOk(await inst.withdraw(accts.beneficiary, invoiceAmount, {from: accts.beneficiary}));
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
    });

    it('Overdue pay', async function() {
        let invoiceAmount = web3.toWei('1.0');

        let inst = await newInstance(Object.assign({
            validityPeriod: now() + 60,
            partialReceiver: accts.beneficiary,
        }, accts));

        let payAmount = web3.toWei('0.1');
        await inst.sendTransaction({from: accts.payer, value: payAmount});
        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(0);

        await passTime(120);

        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(1);
        await expectThrow(inst.sendTransaction({from: accts.payer, value: invoiceAmount}));
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(payAmount);

        await inst.withdraw(accts.beneficiary, payAmount, {from: accts.beneficiary});
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
    });

    it('Over withdraw', async function() {
        let invoiceAmount = web3.toWei('1.0');

        let inst = await newInstance(Object.assign({
            validityPeriod: now() + 1000,
            partialReceiver: accts.beneficiary,
        }, accts));

        await inst.sendTransaction({from: accts.payer, value: invoiceAmount});
        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(2);

        let withdrawAmount = web3.toWei('1.1');
        await expectThrow(inst.withdraw(accts.beneficiary, withdrawAmount, {from: accts.beneficiary}));
    });

    it('Withdraw after validity period if full paid', async function() {
        let invoiceAmount = web3.toWei('1.0');

        let inst = await newInstance(Object.assign({
            validityPeriod: now() + 1000,
            partialReceiver: accts.beneficiary,
        }, accts));

        await inst.sendTransaction({from: accts.payer, value: invoiceAmount});
        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(2);

        passTime(120);

        await inst.withdraw(accts.beneficiary, invoiceAmount, {from: accts.beneficiary});
        await inst.currentAmount({from: accts.anyone}).should.eventually.be.bignumber.equal(0);
        await inst.getStatus({from: accts.payer}).should.eventually.be.bignumber.equal(2);
    });
});


