create database if not exists order_center default character set utf8mb4;
use order_center;

-- 设计理由：支撑用户登录、注册、账号基本信息
create table if not exists `user` (
	`user_id` bigint not null auto_increment comment '用户id,主键',
	`user_name` varchar(50) not null comment '用户名',
	`user_password` varchar(100) not null comment '用户密码',
	`user_nickname` varchar(50) default null comment '用户昵称',
	`user_createtime` datetime not null default current_timestamp comment '创建时间',
	`user_phonenumber` varchar(11) default null comment '手机号',
	primary key(`user_id`),
	unique key uk_user_name(`user_name`)
) engine = InnoDB default charset=utf8mb4;

-- 设计理由：支持用户根据商品类别、商品名查找
create table if not exists `product` (
	`product_id` bigint not null auto_increment comment '商品id,主键',
	`product_name` varchar(100) not null comment '商品名称',
	`product_createtime` datetime not null default current_timestamp comment '创建时间',
	`product_type` varchar(100) default null comment '商品类别',
	`product_amount` decimal(10,2) not null comment '商品价格',
	primary key(`product_id`)
) engine = InnoDB default charset=utf8mb4;

-- 设计理由：根据商品号查询对应商品状态（已售罄/有货）和具体数量
create table if not exists `inventory` (
	`product_id` bigint not null comment '商品id,主键',
	`total_stock` bigint not null comment '总库存',
	`locked_stock` bigint not null comment '锁定库存',
	primary key(`product_id`)
) engine = InnoDB default charset=utf8mb4;

-- 设计理由：得到用户订单的总金额、下单数量、订单状态（是否已支付）
create table if not exists `order` (
	`order_id` bigint not null auto_increment comment '订单id,主键',
	`user_id` bigint not null comment '用户id',
	`order_total_num` int not null comment '下单总数量',
	`order_total_amount` decimal(10,2) not null comment '订单总金额',
	`order_createtime` datetime not null default current_timestamp comment '下单时间',
	`order_updatetime` datetime not null default current_timestamp on update current_timestamp comment '状态变更时间',
	`order_status` tinyint not null default 0 comment '订单状态:0待支付 1已支付 2已完成 3已取消',
	`order_cancel_reason` varchar(256) default null comment '取消原因',
	primary key(`order_id`),
	key `idx_user_id` (`user_id`)
)	engine = InnoDB default charset=utf8mb4;

-- 设计理由：看到用户具体下单商品、下单件数
create table if not exists `order_item` (
	`product_id` bigint not null comment '商品id',
	`order_item_num` int not null comment '下单件数',
	`order_item_amount` decimal(10,2) not null comment '下单时的金额',
	`order_item_subtotal` decimal(10,2) not null comment '下单小计',
	`order_id` bigint not null comment '订单id',
	`product_name` varchar(100) not null comment '下单时商品名',
	primary key(`order_id`, `product_id`),
	key `idx_product_id` (`product_id`)
) engine = InnoDB default charset=utf8mb4;

-- 设计理由：预防重复消息，返回下单返回消息，是否成功下单
create table if not exists `idempotent` (
	`result_msg` varchar(256) not null comment '下单返回消息',
	`request_id` bigint not null comment '请求id,主键',
	`idempotent_status` tinyint not null comment '消息状态:0处理中 1成功 2失败',
	`idempotent_createtime` datetime not null default current_timestamp comment '收到时间',
	primary key(`request_id`)
) engine = InnoDB default charset=utf8mb4;